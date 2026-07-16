"""比价服务（FR-02）。

职责：
1. 标题模糊匹配：把 Sorftime 产品标题提取关键词，查 1688 货源，按相似度排序
2. 利润计算：平台售价 - 1688 拿货价（汇率换算）- FBA费用
3. 预警判定：1688 拿货价变动 >= 5% 触发预警
4. 价格快照：记录每次刷新到 price_snapshots 表
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.sorftime import sorftime_adapter
from app.core.logging import get_logger
from app.models.price_snapshot import PriceSnapshot
from app.models.product import Product

logger = get_logger("services.price_compare")

# USD -> CNY 汇率（MVP 固定值，后续可接实时汇率 API）
USD_TO_CNY = 7.2

# 预警阈值（SRS FR-02 确认值）
PRICE_CHANGE_ALERT_THRESHOLD = 5.0  # ±5%


@dataclass
class MatchResult:
    """单个 1688 匹配结果。"""

    source_id: str          # 1688 ProductId
    title: str
    price_cny: float
    price_usd: float        # 换算为 USD
    sales_30d: Optional[int]
    store_name: str
    similarity: float       # 标题相似度 0-100


@dataclass
class PriceCompareResult:
    """比价综合结果。"""

    product_id: int
    matches: list[MatchResult]
    best_match: Optional[MatchResult]
    platform_price_usd: Optional[float]
    estimated_profit_usd: Optional[float]
    profit_margin: Optional[float]


class PriceCompareService:
    """比价与利润计算服务。"""

    def search_1688(self, product_title: str, top_n: int = 3) -> list[MatchResult]:
        """根据产品标题查 1688 货源，返回相似度排序的匹配列表。"""
        keyword = self._extract_keyword(product_title)
        try:
            raw_items = sorftime_adapter.ali1688_search(keyword)
        except Exception as e:
            logger.error("1688 查询失败", keyword=keyword, error=str(e))
            return []

        results: list[MatchResult] = []
        for item in raw_items:
            title = item.get("Title") or ""
            price_cny = self._to_float(item.get("Price"))
            if not title or price_cny is None:
                continue
            sim = self._similarity(product_title, title)
            results.append(MatchResult(
                source_id=str(item.get("ProductId") or ""),
                title=title,
                price_cny=price_cny,
                price_usd=round(price_cny / USD_TO_CNY, 2),
                sales_30d=self._to_int(item.get("SalesOf30d")),
                store_name=item.get("StoreName") or "",
                similarity=sim,
            ))

        # 按相似度降序，取 top_n
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_n]

    def compare(self, product: Product, top_n: int = 3) -> PriceCompareResult:
        """对单个产品执行比价（含利润计算）。"""
        matches = self.search_1688(product.title, top_n=top_n)
        best = matches[0] if matches else None

        platform_price = float(product.price) if product.price else None
        profit = None
        margin = None
        if best and platform_price:
            profit = round(platform_price - best.price_usd, 2)
            margin = round(profit / platform_price * 100, 2) if platform_price else None

        return PriceCompareResult(
            product_id=product.id,
            matches=matches,
            best_match=best,
            platform_price_usd=platform_price,
            estimated_profit_usd=profit,
            profit_margin=margin,
        )

    def record_snapshot(self, db: Session, product: Product, result: PriceCompareResult,
                        snapshot_date: date) -> Optional[PriceSnapshot]:
        """把比价结果记录为价格快照（含与上次价格的变动计算）。"""
        if not result.best_match:
            return None

        # 查上次快照
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

        platform_price = float(product.price) if product.price else None
        snapshot = PriceSnapshot(
            product_id=product.id,
            price_1688=new_price_cny,
            price_1688_previous=prev_price,
            price_change_percent=change_pct,
            price_platform=platform_price,
            price_platform_previous=float(prev.price_platform) if prev and prev.price_platform else None,
            estimated_profit=result.estimated_profit_usd,
            profit_margin=result.profit_margin,
            snapshot_date=snapshot_date,
        )
        db.add(snapshot)
        return snapshot

    @staticmethod
    def check_alert(change_pct: Optional[float]) -> Optional[str]:
        """根据变动百分比判定预警状态。

        >= +5% 触发成本预警，<= -5% 触发降价利好。
        """
        if change_pct is None:
            return None
        if change_pct >= PRICE_CHANGE_ALERT_THRESHOLD:
            return "cost_alert"     # 成本上涨预警
        if change_pct <= -PRICE_CHANGE_ALERT_THRESHOLD:
            return "price_drop"     # 降价利好
        return None

    # ---------- 辅助 ----------
    @staticmethod
    def _extract_keyword(title: str) -> str:
        """从产品标题提取搜索关键词（去掉品牌词噪音，取核心规格）。"""
        # MVP：去掉常见品牌前缀，截取前几个实词
        noise = {"the", "a", "an", "for", "with", "and", "of", "official", "new"}
        words = [w for w in title.replace(",", " ").split() if w.lower() not in noise]
        return " ".join(words[:6]) if words else title[:40]

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """简单标题相似度：词重叠率（0-100）。"""
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        overlap = len(wa & wb)
        return round(overlap / len(wa | wb) * 100, 1)

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


# 单例
price_compare_service = PriceCompareService()