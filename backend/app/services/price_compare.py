"""比价服务（FR-02 增强版）。

完整外贸成本模型：
  售价(CNY) = 售价(USD) * 汇率
  总成本 = 拿货价 + 国际物流 + 关税 + 平台佣金 + 包装费 + 退货损耗
  毛利润 = 售价(CNY) - 总成本
  毛利率 = 毛利润 / 售价(CNY) * 100%

流程：
1. 英文标题 -> 中文关键词（translator）
2. 中文关键词搜 1688
3. 标题相似度匹配
4. 完整成本核算
5. 价格快照记录 + 预警
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.sorftime import sorftime_adapter
from app.core.logging import get_logger
from app.models.price_snapshot import PriceSnapshot
from app.models.product import Product
from app.services.translator import translate_to_chinese
from app.services.exchange_rate import get_usd_to_cny

logger = get_logger("services.price_compare")

PRICE_CHANGE_ALERT_THRESHOLD = 5.0  # +-5%


# ---------- 成本参数（可后续做成可配置）----------
class CostConfig:
    """外贸成本参数（默认值，可按品类/站点调整）。"""
    INTERNATIONAL_SHIPPING_CNY = 25.0   # 国际物流（每单，海运均摊）
    CUSTOMS_DUTY_RATE = 0.05            # 关税率 5%（普货参考值）
    PLATFORM_COMMISSION_RATE = 0.08     # 平台佣金 8%（TikTok Shop 参考）
    PACKAGING_CNY = 3.0                 # 包装费
    RETURN_LOSS_RATE = 0.03             # 退货损耗 3%（退货产生的运费+折损）


@dataclass
class MatchResult:
    """单个 1688 匹配结果。"""
    source_id: str
    title: str
    title_cn: str                       # 翻译后的中文搜索词
    price_cny: float
    price_usd: float
    sales_30d: Optional[int]
    store_name: str
    similarity: float


@dataclass
class CostBreakdown:
    """完整成本明细（单位 CNY）。"""
    purchase_price: float               # 1688 拿货价
    international_shipping: float       # 国际物流
    customs_duty: float                 # 关税
    platform_commission: float          # 平台佣金
    packaging: float                    # 包装费
    return_loss: float                  # 退货损耗
    total_cost: float                   # 总成本

    @property
    def total_cost_usd(self) -> float:
        from app.services.exchange_rate import get_usd_to_cny
        return round(self.total_cost / get_usd_to_cny(), 2)


@dataclass
class PriceCompareResult:
    """比价综合结果。"""
    product_id: int
    matches: list[MatchResult]
    best_match: Optional[MatchResult]
    search_keyword_cn: str              # 实际搜 1688 用的中文词
    exchange_rate: float                # 用的汇率
    platform_price_usd: Optional[float]
    platform_price_cny: Optional[float]
    cost: Optional[CostBreakdown]       # 成本明细
    gross_profit_cny: Optional[float]   # 毛利润 CNY
    gross_profit_usd: Optional[float]   # 毛利润 USD
    profit_margin: Optional[float]      # 毛利率 %


class PriceCompareService:
    """比价与完整成本核算服务。"""

    def search_1688(self, product_title: str, top_n: int = 3) -> list[MatchResult]:
        """英文标题 -> 中文翻译 -> 搜 1688。"""
        keyword_cn = translate_to_chinese(product_title)
        logger.info("1688 搜索", original=product_title[:40], translated=keyword_cn)

        try:
            raw_items = sorftime_adapter.ali1688_search(keyword_cn)
        except Exception as e:
            logger.error("1688 查询失败", keyword=keyword_cn, error=str(e))
            return []

        results: list[MatchResult] = []
        for item in raw_items:
            title = item.get("Title") or ""
            price_cny = self._to_float(item.get("Price"))
            if not title or price_cny is None:
                continue
            sim = self._similarity(keyword_cn, title)
            results.append(MatchResult(
                source_id=str(item.get("ProductId") or ""),
                title=title,
                title_cn=keyword_cn,
                price_cny=price_cny,
                price_usd=round(price_cny / get_usd_to_cny(), 2),
                sales_30d=self._to_int(item.get("SalesOf30d")),
                store_name=item.get("StoreName") or "",
                similarity=sim,
            ))

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_n]

    def compare(self, product: Product, top_n: int = 3) -> PriceCompareResult:
        """对单个产品执行比价（含完整成本核算）。"""
        matches = self.search_1688(product.title, top_n=top_n)
        best = matches[0] if matches else None

        rate = get_usd_to_cny()
        platform_price_usd = float(product.price) if product.price else None
        # TikTok 价格单位是美元，Amazon 是美分
        if product.platform == "amazon" and platform_price_usd:
            platform_price_usd = platform_price_usd / 100
        platform_price_cny = round(platform_price_usd * rate, 2) if platform_price_usd else None

        cost = None
        profit_cny = None
        profit_usd = None
        margin = None

        if best and platform_price_cny:
            cost = self._calc_cost(best.price_cny, platform_price_cny)
            profit_cny = round(platform_price_cny - cost.total_cost, 2)
            profit_usd = round(profit_cny / rate, 2)
            margin = round(profit_cny / platform_price_cny * 100, 2) if platform_price_cny else None

        return PriceCompareResult(
            product_id=product.id,
            matches=matches,
            best_match=best,
            search_keyword_cn=matches[0].title_cn if matches else "",
            exchange_rate=rate,
            platform_price_usd=platform_price_usd,
            platform_price_cny=platform_price_cny,
            cost=cost,
            gross_profit_cny=profit_cny,
            gross_profit_usd=profit_usd,
            profit_margin=margin,
        )

    def _calc_cost(self, purchase_cny: float, sell_cny: float) -> CostBreakdown:
        """完整成本核算（单位 CNY）。"""
        cfg = CostConfig
        shipping = cfg.INTERNATIONAL_SHIPPING_CNY
        duty = round(purchase_cny * cfg.CUSTOMS_DUTY_RATE, 2)
        commission = round(sell_cny * cfg.PLATFORM_COMMISSION_RATE, 2)
        packaging = cfg.PACKAGING_CNY
        return_loss = round(sell_cny * cfg.RETURN_LOSS_RATE, 2)
        total = round(purchase_cny + shipping + duty + commission + packaging + return_loss, 2)
        return CostBreakdown(
            purchase_price=purchase_cny,
            international_shipping=shipping,
            customs_duty=duty,
            platform_commission=commission,
            packaging=packaging,
            return_loss=return_loss,
            total_cost=total,
        )

    def record_snapshot(self, db: Session, product: Product, result: PriceCompareResult,
                        snapshot_date: date) -> Optional[PriceSnapshot]:
        """记录价格快照（含成本明细）。"""
        if not result.best_match:
            return None

        prev = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product.id)
            .order_by(PriceSnapshot.snapshot_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        prev_price = float(prev.price_1688) if prev and prev.price_1688 else None
        new_price_cny = result.best_match.price_cny
        change_pct = None
        if prev_price and prev_price > 0:
            change_pct = round((new_price_cny - prev_price) / prev_price * 100, 2)

        cost = result.cost
        snapshot = PriceSnapshot(
            product_id=product.id,
            price_1688=new_price_cny,
            price_1688_previous=prev_price,
            price_change_percent=change_pct,
            price_platform=result.platform_price_cny,
            price_platform_previous=float(prev.price_platform) if prev and prev.price_platform else None,
            estimated_profit=result.gross_profit_usd,
            profit_margin=result.profit_margin,
            cost_shipping=cost.international_shipping if cost else None,
            cost_customs=cost.customs_duty if cost else None,
            cost_commission=cost.platform_commission if cost else None,
            cost_packaging=cost.packaging if cost else None,
            cost_return_loss=cost.return_loss if cost else None,
            total_cost=cost.total_cost if cost else None,
            matched_title=result.best_match.title if result.best_match else None,
            search_keyword_cn=result.search_keyword_cn or None,
            similarity=result.best_match.similarity if result.best_match else None,
            exchange_rate=result.exchange_rate,
            snapshot_date=snapshot_date,
        )
        db.add(snapshot)
        return snapshot

    @staticmethod
    def check_alert(change_pct: Optional[float]) -> Optional[str]:
        if change_pct is None:
            return None
        if change_pct >= PRICE_CHANGE_ALERT_THRESHOLD:
            return "cost_alert"
        if change_pct <= -PRICE_CHANGE_ALERT_THRESHOLD:
            return "price_drop"
        return None

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """中文标题相似度：字符二元组重叠率。"""
        if not a or not b:
            return 0.0
        # 用字符 bigram
        def bigrams(s):
            s = s.replace(" ", "")
            return set(s[i:i+2] for i in range(len(s) - 1)) if len(s) > 1 else {s}
        ba, bb = bigrams(a), bigrams(b)
        if not ba or not bb:
            return 0.0
        overlap = len(ba & bb)
        return round(overlap / len(ba | bb) * 100, 1)

    @staticmethod
    def _to_float(v) -> Optional[float]:
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_int(v) -> Optional[int]:
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


price_compare_service = PriceCompareService()
