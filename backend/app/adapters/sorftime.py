"""Sorftime 亚马逊数据 API 适配层。

对接「附录A-Sorftime接口规格.md」的 13 个接口，统一提供：
- 重试（tenacity 指数退避）+ 超时
- 降级（失败时返回缓存/昨日快照，由调用方决定）
- Redis 缓存（高消耗接口强缓存，TTL 24h）
- 容错解析（Sorftime 返回面向 AI 的非严格 JSON 字符串）

外部 API 异常一律转为本系统错误码 2001（超时）/2002（失败），不向上抛原始栈。
"""

import json
import logging
import re
from typing import Any, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.response import BizError, ErrorCode
from app.core.logging import get_logger
from app.schemas.sorftime import (
    CustomersSay,
    CustomersSayKeyword,
    ProductDetail,
    ProductListItem,
    Review,
    SimilarFeature,
    TrafficTerm,
    Variation,
)

logger = get_logger("adapters.sorftime")

CACHE_TTL_SECONDS = 24 * 3600
DEFAULT_TIMEOUT = 30


# ---------- 容错解析 ----------

def _parse_lenient(raw: Any) -> Any:
    """尝试把 Sorftime 面向 AI 的字符串解析为 Python 对象。

    优先 json.loads；失败则尝试从字符串里提取首个 JSON 数组/对象。
    均失败时原样返回字符串。
    """
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return raw

    text = raw.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 尝试截取第一个 [ ... ] 或 { ... }
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            snippet = text[start : end + 1]
            try:
                return json.loads(snippet)
            except (json.JSONDecodeError, ValueError):
                continue
    return text


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(re.sub(r"[^0-9.\-]", "", str(v)))
    except (ValueError, TypeError):
        return None


def _to_int(v: Any) -> Optional[int]:
    f = _to_float(v)
    return int(f) if f is not None else None


# ---------- 适配层主体 ----------

class SorftimeAdapter:
    """Sorftime API 适配层。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        redis_client: Any = None,
    ):
        self.api_key = api_key if api_key is not None else settings.sorftime_api_key
        self.base_url = (base_url or settings.sorftime_base_url).rstrip("/")
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
    def _cache_key(method: str, params: dict) -> str:
        return f"sorftime:{method}:{json.dumps(params, sort_keys=True, ensure_ascii=False)}"

    # ----- 底层调用 -----
    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _call(self, method: str, params: dict, use_cache: bool = True) -> Any:
        """统一请求入口：带重试、超时、缓存。失败转 BizError。"""
        cache_key = self._cache_key(method, params)
        if use_cache:
            cached = self._cache_get(cache_key)
            if cached is not None:
                logger.info("Sorftime 命中缓存", method=method)
                return cached

        if not self.api_key:
            raise BizError(
                ErrorCode.API_FAILED, "Sorftime API Key 未配置，无法调用"
            )

        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/v1/{method}"
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(url, headers=headers, json=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as e:
            logger.error("Sorftime 调用超时", method=method)
            raise BizError(ErrorCode.API_TIMEOUT, f"Sorftime 调用超时: {method}") from e
        except httpx.HTTPError as e:
            logger.error("Sorftime 调用失败", method=method, error=str(e))
            raise BizError(ErrorCode.API_FAILED, f"Sorftime 调用失败: {method}") from e

        if use_cache:
            self._cache_set(cache_key, data)
        return data

    # ===== 13 个业务接口 =====

    # 1. 相似产品特征
    def similar_product_feature(self, amz_site: str, product_name: str) -> list[SimilarFeature]:
        raw = self._call("similar_product_feature", {"amzSite": amz_site, "productName": product_name})
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(data, list):
            return []
        return [
            SimilarFeature(
                feature=item.get("产品特点") or item.get("feature"),
                product_share=item.get("产品数量占比") or item.get("product_share"),
                sales_share=item.get("月销量占比") or item.get("sales_share"),
                description=item.get("产品特点说明") or item.get("description"),
            )
            for item in data
            if isinstance(item, dict)
        ]

    # 2. 产品详情
    def product_detail(self, amz_site: str, asin: str) -> ProductDetail:
        raw = self._call("product_detail", {"amzSite": amz_site, "asin": asin})
        d = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(d, dict):
            d = {}
        return ProductDetail(
            asin=d.get("产品ASIN码") or asin,
            parent_asin=d.get("父级ASIN码"),
            title=d.get("标题"),
            image=d.get("主图"),
            price=_to_float(d.get("价格")),
            rating=_to_float(d.get("星级")),
            ratings_count=_to_int(d.get("评论数")),
            brand=d.get("品牌"),
            monthly_sales=_to_int(re.sub(r"\D", "", str(d.get("月销量", ""))) or None),
            monthly_revenue=_to_float(re.sub(r"[^\d.]", "", str(d.get("月销额", ""))) or None),
            gross_profit=_to_float(d.get("毛利")),
            gross_margin=_to_float(d.get("毛利率")),
            fba_fee=_to_float(d.get("FBA费用")),
            package_size=d.get("外包装尺寸（cm）") or d.get("包装尺寸"),
            weight_g=_to_int(d.get("重量（g）") or d.get("重量")),
            aplus=d.get("APlus"),
            raw=d,
        )

    # 3. 产品变体查询
    def product_variations(self, amz_site: str, asin: str) -> list[Variation]:
        raw = self._call("product_variations", {"amzSite": amz_site, "asin": asin})
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        results: list[Variation] = []
        if isinstance(data, list):
            for line in data:
                if isinstance(line, str):
                    child = re.search(r"子体：([A-Z0-9]+)", line)
                    attr = re.search(r"属性：(.+?)，子体月销量", line)
                    sales = re.search(r"子体月销量：([\d\-]+)", line)
                    results.append(Variation(
                        asin=child.group(1) if child else "",
                        attribute=attr.group(1) if attr else None,
                        monthly_sales_range=sales.group(1) if sales else None,
                    ))
                elif isinstance(line, dict):
                    results.append(Variation(
                        asin=line.get("asin", ""),
                        attribute=line.get("attribute"),
                        monthly_sales_range=line.get("monthly_sales_range"),
                    ))
        return results

    # 4. 产品历史趋势
    def product_trend(self, amz_site: str, asin: str, trend_type: str = "SalesVolume") -> list[dict]:
        raw = self._call(
            "product_trend",
            {"amzSite": amz_site, "asin": asin, "productTrendType": trend_type},
        )
        text = raw.get("data", raw) if isinstance(raw, dict) else raw
        if isinstance(text, dict):
            return [{"date": k, "value": v} for k, v in text.items()]
        if isinstance(text, str):
            pairs = re.findall(r"(\d{4}年\d{1,2}月)=([\d.]+)", text)
            return [{"date": d, "value": _to_float(v)} for d, v in pairs]
        return []

    # 5. 产品评论
    def product_reviews(self, amz_site: str, asin: str, review_type: str = "Both") -> list[Review]:
        raw = self._call(
            "product_reviews",
            {"amzSite": amz_site, "asin": asin, "reviewType": review_type},
            use_cache=True,  # 高消耗，强缓存
        )
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(data, list):
            return []
        return [
            Review(
                attribute=item.get("评论产品的属性"),
                date=item.get("评论日期"),
                rating=_to_float(item.get("评星")),
                title=item.get("标题"),
                content=item.get("评论"),
            )
            for item in data
            if isinstance(item, dict)
        ]

    # 6. 潜力产品搜索
    def potential_product(self, amz_site: str, **filters: Any) -> list[ProductListItem]:
        params = {"amzSite": amz_site, **filters}
        raw = self._call("potential_product", params)
        return self._parse_product_list(raw)

    # 7. 选产品（实时）
    def product_search(self, amz_site: str, **filters: Any) -> list[ProductListItem]:
        params = {"amzSite": amz_site, **filters}
        raw = self._call("product_search", params)
        return self._parse_product_list(raw)

    # 8. 产品流量词反查
    def product_traffic_terms(self, amz_site: str, asin: str, page: int = 1) -> list[TrafficTerm]:
        raw = self._call("product_traffic_terms", {"amzSite": amz_site, "asin": asin, "page": page})
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(data, list):
            return []
        return [
            TrafficTerm(
                keyword=item.get("关键词") or item.get("keyword", ""),
                monthly_search_volume=_to_int(item.get("月搜索量")),
                suggested_bid=item.get("推荐竞价"),
                position=item.get("曝光位置"),
            )
            for item in data
            if isinstance(item, dict)
        ]

    # 9. 竞品关键词分析（注意字段名 keywordSupportSite）
    def competitor_product_keywords(self, amz_site: str, asin: str, page: int = 1) -> list[TrafficTerm]:
        raw = self._call(
            "competitor_product_keywords",
            {"keywordSupportSite": amz_site, "asin": asin, "page": page},
        )
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(data, list):
            return []
        return [
            TrafficTerm(
                keyword=item.get("关键词") or item.get("keyword", ""),
                monthly_search_volume=_to_int(item.get("关键词月搜索量") or item.get("月搜索量")),
                suggested_bid=None,
                position=item.get("曝光位置"),
            )
            for item in data
            if isinstance(item, dict)
        ]

    # 10. 产品关键词排名趋势
    def product_ranking_trend_by_keyword(
        self, amz_site: str, asin: str, keyword: str, page: int = 1
    ) -> list[dict]:
        raw = self._call(
            "product_ranking_trend_by_keyword",
            {"amzSite": amz_site, "asin": asin, "keyword": keyword, "page": page},
        )
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(data, list):
            return []
        return [
            {"page": item.get("page"), "position": item.get("position"), "time": item.get("time")}
            for item in data
            if isinstance(item, dict)
        ]

    # 11. 产品分析报告（工作流引导，本身无数据）
    def product_report(self, amz_site: str, asin: str) -> str:
        raw = self._call("product_report", {"amzSite": amz_site, "asin": asin}, use_cache=False)
        if isinstance(raw, dict):
            return str(raw.get("data") or raw.get("message") or "")
        return str(raw)

    # 12. 选产品（历史）
    def product_search_from_history(self, amz_site: str, search_time: str, **filters: Any) -> list[ProductListItem]:
        params = {"amzSite": amz_site, "searchTime": search_time, **filters}
        raw = self._call("product_search_from_history", params)
        return self._parse_product_list(raw)

    # 13. 亚马逊总结产品评论（注意字段名 site）
    def product_customers_say(self, amz_site: str, asin: str) -> CustomersSay:
        raw = self._call("product_customers_say", {"site": amz_site, "asin": asin})
        d = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(d, dict):
            d = {}
        kw_list = d.get("评论关键词分析") or d.get("keywords") or []
        keywords = []
        if isinstance(kw_list, list):
            for kw in kw_list:
                if not isinstance(kw, dict):
                    continue
                keywords.append(CustomersSayKeyword(
                    keyword=kw.get("关键词") or kw.get("keyword", ""),
                    description=kw.get("描述"),
                    total_mentions=_to_int(kw.get("总提及次数")),
                    positive_count=_to_int(kw.get("积极评论数")),
                    negative_count=_to_int(kw.get("消极评论数")),
                ))
        return CustomersSay(
            asin=d.get("产品ASIN码") or asin,
            ai_summary=d.get("AI评论总结"),
            keywords=keywords,
        )

    # ----- 列表解析复用 -----
    def _parse_product_list(self, raw: Any) -> list[ProductListItem]:
        data = _parse_lenient(raw.get("data", raw) if isinstance(raw, dict) else raw)
        if not isinstance(data, list):
            return []
        items: list[ProductListItem] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            items.append(ProductListItem(
                asin=item.get("产品ASIN码") or item.get("asin", ""),
                parent_asin=item.get("父级ASIN码"),
                title=item.get("标题"),
                image=item.get("主图"),
                price=_to_float(item.get("价格")),
                rating=_to_float(item.get("星级")),
                ratings_count=_to_int(item.get("评论数")),
                brand=item.get("品牌"),
                monthly_sales=_to_int(item.get("月销量")),
                monthly_revenue=_to_float(item.get("月销额")),
                potential_index=_to_float(item.get("产品潜力指数")),
                delivery_type=item.get("发货方式"),
                seller_country=item.get("卖家国籍"),
                aplus=item.get("APlus"),
                raw=item,
            ))
        return items


# 单例
sorftime_adapter = SorftimeAdapter()