"""Sorftime Standard API 适配层。

对接 Sorftime Standard API（standardapi.sorftime.com），统一提供：
- BasicAuth 认证（Authorization: BasicAuth <Account-SK>）
- PascalCase 接口名 + 数字 domain（Amazon 1-14，1688 为 601）
- 重试（tenacity 指数退避）+ 超时
- Redis 缓存（高消耗接口强缓存，TTL 24h）
- 统一返回解析（Code=0 为成功，非 0 转业务错误；字段 PascalCase）

覆盖核心接口：
- Amazon: ProductRequest / ProductSearch / AsinSalesVolume / ProductVariationHistory
- Amazon: ProductReviewsCollection + ProductReviewsQuery
- 1688:   ProductSearchFromName (domain=601)

外部 API 异常一律转为本系统错误码 2001（超时）/2002（失败），不向上抛原始栈。
"""

import json
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.core.response import BizError, ErrorCode
from app.schemas.sorftime import (
    ProductDetail,
    ProductListItem,
    Review,
    Variation,
)

logger = get_logger("adapters.sorftime")

CACHE_TTL_SECONDS = 24 * 3600
DEFAULT_TIMEOUT = 30

# Amazon 站点代码 -> domain 数字
AMAZON_DOMAIN_MAP = {
    "US": 1, "GB": 2, "UK": 2, "DE": 3, "FR": 4, "IN": 5, "CA": 6,
    "JP": 7, "ES": 8, "IT": 9, "MX": 10, "AE": 11, "AU": 12, "BR": 13, "SA": 14,
}
ALI1688_DOMAIN = 601

# TikTok 站点代码 -> domain 数字
TIKTOK_DOMAIN_MAP = {
    "US": 301, "MY": 303, "PH": 304, "VN": 305,
    "TH": 306, "ID": 307, "GB": 309, "JP": 312,
}


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _to_str(v: Any) -> Optional[str]:
    """兼容 Sorftime 返回的字符串或列表（取首项或拼接）。"""
    if v is None:
        return None
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) if v else None
    return str(v)


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        f = _to_float(v)
        return int(f) if f is not None else None


class SorftimeAdapter:
    """Sorftime Standard API 适配层。"""

    def __init__(self, sk: Optional[str] = None, base_url: Optional[str] = None, redis_client: Any = None):
        raw_sk = sk if sk is not None else (settings.sorftime_api_sk or settings.sorftime_api_key)
        # 支持逗号分隔多 key，额度不足时自动轮换
        self.sk_list = [k.strip() for k in raw_sk.split(",") if k.strip()] if raw_sk else []
        self.sk = self.sk_list[0] if self.sk_list else ""
        self.sk_index = 0
        self.base_url = (base_url or settings.sorftime_api_base_url).rstrip("/")
        self.redis = redis_client

    # ----- 缓存 -----
    def _cache_get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("缓存读取失败", key=key, error=str(e))
        return None

    def _cache_set(self, key: str, value: Any, ttl: int = CACHE_TTL_SECONDS) -> None:
        if not self.redis:
            return
        try:
            self.redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        except Exception as e:
            logger.warning("缓存写入失败", key=key, error=str(e))

    @staticmethod
    def _cache_key(endpoint: str, domain: int, params: dict) -> str:
        return f"sorftime:{endpoint}:{domain}:{json.dumps(params, sort_keys=True, ensure_ascii=False)}"

    # ----- 站点映射 -----
    @staticmethod
    def _domain(site: str) -> int:
        """解析 Amazon 站点代码为 domain 数字。"""
        key = (site or "").upper()
        if key in AMAZON_DOMAIN_MAP:
            return AMAZON_DOMAIN_MAP[key]
        raise BizError(ErrorCode.PARAM_INVALID, f"不支持的亚马逊站点: {site}")

    @staticmethod
    def _tiktok_domain(site: str) -> int:
        """解析 TikTok 站点代码为 domain 数字。"""
        key = (site or "").upper()
        if key in TIKTOK_DOMAIN_MAP:
            return TIKTOK_DOMAIN_MAP[key]
        raise BizError(ErrorCode.PARAM_INVALID, f"不支持的 TikTok 站点: {site}")

    # 额度不足的错误码（遇到则自动切换下一个 key）
    QUOTA_ERROR_CODES = {694, 500, 501, 502}

    def _next_key(self) -> bool:
        """切换到下一个 key，返回是否还有可用 key。"""
        if len(self.sk_list) <= 1:
            return False
        self.sk_index = (self.sk_index + 1) % len(self.sk_list)
        self.sk = self.sk_list[self.sk_index]
        logger.warning("Sorftime key 轮换", index=self.sk_index, key_prefix=self.sk[:8])
        return self.sk_index != 0  # 轮了一圈回到 0 则表示全部试过

    # ----- 底层调用 -----
    def _call(self, endpoint: str, domain: int, params: dict, use_cache: bool = True) -> dict:
        """统一请求入口：BasicAuth + POST + domain 参数。

        支持多 key 轮换：遇到额度不足（694/500/501/502）自动切换下一个 key。
        """
        cache_key = self._cache_key(endpoint, domain, params)
        if use_cache:
            cached = self._cache_get(cache_key)
            if cached is not None:
                logger.info("Sorftime 命中缓存", endpoint=endpoint, domain=domain)
                return cached

        if not self.sk_list:
            raise BizError(ErrorCode.API_FAILED, "Sorftime Account-SK 未配置")

        url = f"{self.base_url}/{endpoint}?domain={domain}"
        max_attempts = len(self.sk_list)

        for attempt in range(max_attempts):
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "Authorization": f"BasicAuth {self.sk}",
            }
            try:
                with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                    resp = client.post(url, headers=headers, json=params)
                    resp.raise_for_status()
                    data = resp.json()
            except httpx.TimeoutException as e:
                logger.error("Sorftime 调用超时", endpoint=endpoint)
                raise BizError(ErrorCode.API_TIMEOUT, f"Sorftime 调用超时: {endpoint}") from e
            except httpx.HTTPError as e:
                logger.error("Sorftime 调用失败", endpoint=endpoint, error=str(e))
                raise BizError(ErrorCode.API_FAILED, f"Sorftime 调用失败: {endpoint}") from e

            code = data.get("Code", data.get("code", -1))
            if code == 0:
                if use_cache:
                    self._cache_set(cache_key, data)
                return data

            msg = data.get("Message", data.get("message", "未知错误"))

            # 额度不足 -> 尝试下一个 key
            if code in self.QUOTA_ERROR_CODES and self._next_key():
                logger.warning(
                    "Sorftime 额度不足，切换 key 重试",
                    endpoint=endpoint, code=code, msg=msg, attempt=attempt + 1,
                )
                continue

            self._handle_error_code(code, msg, endpoint)
            raise BizError(ErrorCode.API_FAILED, f"Sorftime {endpoint} 失败: {msg} (Code={code})")

        raise BizError(ErrorCode.API_FAILED, f"Sorftime {endpoint} 所有 key 额度均不足")

    @staticmethod
    def _data(raw: dict) -> Any:
        """从返回体取 Data（大小写兼容）。"""
        return raw.get("Data", raw.get("data"))

    @staticmethod
    def _handle_error_code(code: int, message: str, endpoint: str) -> None:
        hints = {
            4: "积分余额不足",
            400: "IP 未在白名单",
            401: "接口未开放或套餐不含",
            500: "本月请求数已达限额",
            501: "一分钟内请求已达限额",
            502: "一天内请求已达限额",
            694: "请求剩余量不足",
        }
        hint = hints.get(code)
        if hint:
            logger.error("Sorftime 业务错误", endpoint=endpoint, code=code, hint=hint, message=message)

    # ===== Amazon 产品接口 =====

    # 1. 产品详情 ProductRequest（消耗 1）
    def product_detail(self, amz_site: str, asin: str, trend: int = 1) -> ProductDetail:
        domain = self._domain(amz_site)
        raw = self._call("ProductRequest", domain, {"asin": asin, "trend": trend})
        d = self._data(raw) or {}
        if isinstance(d, list):
            d = d[0] if d else {}
        if not isinstance(d, dict):
            d = {}
        return self._parse_product_detail(d)

    # 2. 产品搜索 ProductSearch（消耗 5）
    def product_search(self, amz_site: str, **filters: Any) -> list[ProductListItem]:
        domain = self._domain(amz_site)
        raw = self._call("ProductSearch", domain, filters)
        data = self._data(raw) or {}
        products = data.get("Products") or data.get("products") if isinstance(data, dict) else data
        if not isinstance(products, list):
            return []
        return [self._parse_product_list_item(p) for p in products if isinstance(p, dict)]

    # 3. 子体销量历史 AsinSalesVolume（消耗 1）
    def asin_sales_volume(self, amz_site: str, asin: str, query_date: str = "", query_end_date: str = "") -> list[dict]:
        domain = self._domain(amz_site)
        params = {"asin": asin}
        if query_date:
            params["queryDate"] = query_date
        if query_end_date:
            params["queryEndDate"] = query_end_date
        raw = self._call("AsinSalesVolume", domain, params)
        data = self._data(raw) or []
        if not isinstance(data, list):
            return []
        return [{"date": row[0], "sales": row[1], "type": row[2]} for row in data if isinstance(row, list) and len(row) >= 3]

    # 4. 子体变化历史 ProductVariationHistory（消耗 1）
    def product_variation_history(self, amz_site: str, asin: str) -> list[Variation]:
        domain = self._domain(amz_site)
        raw = self._call("ProductVariationHistory", domain, {"asin": asin})
        data = self._data(raw) or []
        if not isinstance(data, list):
            return []
        results: list[Variation] = []
        for row in data:
            if isinstance(row, list) and len(row) >= 3:
                for child_asin in row[2:]:
                    results.append(Variation(asin=child_asin, attribute=None, monthly_sales_range=None))
        return results

    # 5. 评论采集 ProductReviewsCollection（消耗积分，0 request）
    def product_reviews_collection(self, amz_site: str, asin: str) -> dict:
        domain = self._domain(amz_site)
        raw = self._call("ProductReviewsCollection", domain, {"asin": asin}, use_cache=False)
        return self._data(raw) or {}

    # 6. 评论查询 ProductReviewsQuery（消耗 1）
    def product_reviews_query(self, amz_site: str, asin: str, page: int = 1) -> list[Review]:
        domain = self._domain(amz_site)
        raw = self._call("ProductReviewsQuery", domain, {"asin": asin, "page": page})
        data = self._data(raw) or []
        if not isinstance(data, list):
            return []
        reviews = []
        for item in data:
            if not isinstance(item, dict):
                continue
            reviews.append(Review(
                attribute=item.get("Attribute") or item.get("attribute") or item.get("Variation"),
                date=str(item.get("Date") or item.get("date") or item.get("ReviewDate") or ""),
                rating=_to_float(item.get("Rating") or item.get("rating") or item.get("Star")),
                title=item.get("Title") or item.get("title"),
                content=item.get("Content") or item.get("content") or item.get("Review"),
            ))
        return reviews

    # ===== 1688 采购货源接口 =====

    # 1688 产品搜索 ProductSearchFromName（消耗 1，domain=601）
    def ali1688_search(self, name: str) -> list[dict]:
        """查询 1688 采购货源，用于比价与利润评估。

        返回原始字段（Title/Price/SalesOf30d/WholesalePriceRange 等），
        由 services/price_compare.py 做进一步利润计算。
        """
        raw = self._call("ProductSearchFromName", ALI1688_DOMAIN, {"name": name})
        data = self._data(raw) or []
        return data if isinstance(data, list) else []

    # ===== 解析辅助 =====

    @staticmethod
    def _g(d: dict, *keys: str) -> Any:
        """从 dict 中按多个候选键取值（大小写兼容，PascalCase/camelCase 互查）。"""
        for k in keys:
            if k in d:
                return d[k]
            if k:
                lower = k[0].lower() + k[1:]
                upper = k[0].upper() + k[1:]
                for alt in (lower, upper):
                    if alt in d:
                        return d[alt]
        return None

    @classmethod
    def _parse_product_detail(cls, d: dict) -> ProductDetail:
        return ProductDetail(
            asin=cls._g(d, "Asin", "asin", "ASIN") or "",
            parent_asin=cls._g(d, "ParentAsin", "parentAsin", "parentasin"),
            title=cls._g(d, "Title", "title"),
            image=_to_str(cls._g(d, "Photo", "photo", "Image", "image", "ImgUrl")),
            price=_to_float(cls._g(d, "Price", "price")),
            rating=_to_float(cls._g(d, "Ratings", "Star", "star", "rating")),
            ratings_count=_to_int(cls._g(d, "RatingsCount", "Comments", "comments", "CommentCount")),
            brand=cls._g(d, "Brand", "brand"),
            monthly_sales=_to_int(cls._g(d, "AsinSalesCount", "MonthSales", "monthSales", "SalesVolume")),
            monthly_revenue=_to_float(cls._g(d, "MonthSalesAmount", "Revenue", "revenue")),
            gross_profit=_to_float(cls._g(d, "Profit", "profit", "GrossProfit")),
            gross_margin=_to_float(cls._g(d, "ProfitRate", "profitRate", "Margin")),
            fba_fee=_to_float(cls._g(d, "FbaFee", "fbaFee", "FBA")),
            package_size=_to_str(cls._g(d, "Size", "size", "PackageSize", "Dimension")),
            weight_g=_to_int(cls._g(d, "Weight", "weight", "PackageWeight")),
            aplus=cls._g(d, "APlus", "aplus", "aPlus"),
            seller_country=cls._g(d, "ShipsFrom", "SellerCountry", "sellerCountry"),
            raw=d,
        )

    @classmethod
    def _parse_product_list_item(cls, p: dict) -> ProductListItem:
        d = cls._parse_product_detail(p)
        return ProductListItem(
            asin=d.asin,
            parent_asin=d.parent_asin,
            title=d.title,
            image=d.image,
            price=d.price,
            rating=d.rating,
            ratings_count=d.ratings_count,
            brand=d.brand,
            monthly_sales=d.monthly_sales,
            monthly_revenue=d.monthly_revenue,
            potential_index=_to_float(cls._g(p, "PotentialIndex", "potentialIndex", "Potential")),
            delivery_type=cls._g(p, "ShippingType", "shippingType", "DeliveryType"),
            seller_country=d.seller_country,
            aplus=d.aplus,
            raw=p,
        )

    # ===== TikTok 产品接口 =====

    def tiktok_product_search(self, site: str, name: str, page: int = 1) -> list[ProductListItem]:
        """TikTok 按名称搜索产品（ProductSearchFromName，消耗 5）。

        site: TikTok 站点代码（US/JP/GB 等）
        name: 产品关键词
        返回统一 ProductListItem 列表（字段映射 TikTok -> 统一格式）。
        """
        domain = self._tiktok_domain(site)
        raw = self._call("ProductSearchFromName", domain, {"Name": name, "Page": page})
        data = self._data(raw)
        if not isinstance(data, list):
            return []
        return [self._parse_tiktok_product(p) for p in data if isinstance(p, dict)]

    @staticmethod
    def _parse_tiktok_product(p: dict) -> ProductListItem:
        """将 TikTok ProductSummeryObject 映射为统一 ProductListItem。

        TikTok 字段差异：
        - ProductId（非 asin）
        - Price（非 SalesPrice），单位美元（非美分）
        - MonthlySaleCount（非 ListingSalesVolumeOfMonth）
        - ReviewCount（非 RatingsCount）
        """
        return ProductListItem(
            asin=str(SorftimeAdapter._g(p, "ProductId", "productId") or ""),
            parent_asin=None,
            title=SorftimeAdapter._g(p, "Title", "title") or "",
            image=SorftimeAdapter._g(p, "Image", "MainImage", "image"),
            price=_to_float(SorftimeAdapter._g(p, "Price", "price")),
            rating=_to_float(SorftimeAdapter._g(p, "Star", "Rating", "star", "rating")),
            ratings_count=_to_int(SorftimeAdapter._g(p, "ReviewCount", "reviewCount")),
            brand=SorftimeAdapter._g(p, "Brand", "brand"),
            monthly_sales=_to_int(SorftimeAdapter._g(p, "MonthlySaleCount", "monthlySaleCount")),
            monthly_revenue=_to_float(SorftimeAdapter._g(p, "MonthlySalesAmount", "monthlySalesAmount")),
            potential_index=None,
            delivery_type=None,
            seller_country=SorftimeAdapter._g(p, "Location", "location"),
            aplus=None,
            raw=p,
        )


# 单例
sorftime_adapter = SorftimeAdapter()