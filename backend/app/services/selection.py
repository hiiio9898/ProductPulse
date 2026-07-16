"""选品算法引擎（FR-01）。

职责：
1. 阈值过滤：按用户配置的阈值筛出"低竞争、有利润"的产品
2. 综合评分：多维加权打分（销量/竞争/利润/新品活力）
3. 推荐理由生成：说明通过/未通过原因

阈值来自 system_configs 表的 algorithm.thresholds，可被配置中心动态修改。
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.system_config import SystemConfig


# ---------- 阈值定义 ----------

@dataclass
class Thresholds:
    """选品阈值。通用值来自 SRS FR-01，可被配置中心覆盖。"""

    monthly_sales_min: int = 5000
    monthly_sales_max: int = 150000
    listing_monopoly: float = 30.0
    brand_monopoly: float = 40.0
    seller_monopoly: float = 40.0
    new_product_ratio: float = 5.0
    amazon_self_ratio: float = 30.0
    review_count_max: int = 300

    # 打印耗材特殊阈值（category 匹配 3D 耗材时使用）
    filament_sales_min: int = 3000
    filament_sales_max: int = 200000
    filament_listing_monopoly: float = 25.0
    filament_brand_monopoly: float = 35.0
    filament_seller_monopoly: float = 35.0
    filament_new_ratio: float = 10.0
    filament_review_max: int = 200

    @classmethod
    def from_config(cls, config_value: dict) -> "Thresholds":
        """从 system_configs 的 JSON 构建（缺失字段用默认）。"""
        t = cls()
        for k, v in config_value.items():
            if hasattr(t, k):
                setattr(t, k, v)
        return t

    def for_category(self, category: Optional[str]) -> "Thresholds":
        """返回适用于指定品类的阈值（耗材品类用特殊值）。"""
        cat = (category or "").lower()
        is_filament = any(k in cat for k in ("3d", "耗材", "filament", "打印"))
        if not is_filament:
            return self
        return Thresholds(
            monthly_sales_min=self.filament_sales_min,
            monthly_sales_max=self.filament_sales_max,
            listing_monopoly=self.filament_listing_monopoly,
            brand_monopoly=self.filament_brand_monopoly,
            seller_monopoly=self.filament_seller_monopoly,
            new_product_ratio=self.filament_new_ratio,
            amazon_self_ratio=self.amazon_self_ratio,
            review_count_max=self.filament_review_max,
        )


# ---------- 评分权重 ----------

SCORE_WEIGHTS = {
    "sales": 0.30,       # 销量健康度
    "competition": 0.35, # 竞争度（垄断系数越低越好）
    "profit": 0.20,      # 利润空间
    "vitality": 0.15,    # 新品活力
}


@dataclass
class SelectionResult:
    """单个产品的选品结果。"""

    product: Product
    passed: bool
    score: float
    fail_reasons: list = field(default_factory=list)
    score_breakdown: dict = field(default_factory=dict)


class SelectionEngine:
    """选品算法引擎。"""

    def __init__(self, thresholds: Optional[Thresholds] = None):
        self.default_thresholds = thresholds or Thresholds()

    # ----- 阈值过滤 -----
    def check_product(self, product: Product, thresholds: Optional[Thresholds] = None) -> SelectionResult:
        """对单个产品执行阈值过滤，返回是否通过及未通过原因。"""
        t = (thresholds or self.default_thresholds).for_category(product.category)
        reasons: list[str] = []

        sales = product.monthly_sales or 0
        if not (t.monthly_sales_min <= sales <= t.monthly_sales_max):
            reasons.append(f"月销量 {sales} 不在区间 [{t.monthly_sales_min}, {t.monthly_sales_max}]")

        if product.listing_monopoly is not None and product.listing_monopoly > t.listing_monopoly:
            reasons.append(f"Listing垄断系数 {product.listing_monopoly}% > {t.listing_monopoly}%")

        if product.brand_monopoly is not None and product.brand_monopoly > t.brand_monopoly:
            reasons.append(f"品牌垄断系数 {product.brand_monopoly}% > {t.brand_monopoly}%")

        if product.seller_monopoly is not None and product.seller_monopoly > t.seller_monopoly:
            reasons.append(f"卖家垄断系数 {product.seller_monopoly}% > {t.seller_monopoly}%")

        if product.new_product_ratio is not None and product.new_product_ratio < t.new_product_ratio:
            reasons.append(f"新品占比 {product.new_product_ratio}% < {t.new_product_ratio}%")

        if product.amazon_self_ratio is not None and product.amazon_self_ratio > t.amazon_self_ratio:
            reasons.append(f"亚马逊自营占比 {product.amazon_self_ratio}% > {t.amazon_self_ratio}%")

        if product.review_count is not None and product.review_count > t.review_count_max:
            reasons.append(f"评论数 {product.review_count} > {t.review_count_max}")

        # 评分（加权汇总为综合评分，对应 products.comprehensive_score）
        breakdown = self._score_product(product, t)
        total = self.compute_comprehensive_score(breakdown)

        return SelectionResult(
            product=product,
            passed=len(reasons) == 0,
            score=total,
            fail_reasons=reasons,
            score_breakdown=breakdown,
        )

    # ----- 多维加权评分 -----
    @staticmethod
    def _score_product(product: Product, t: Thresholds) -> dict:
        """计算各维度 0-100 分，返回明细。"""
        scores = {}

        # 销量健康度：在区间中段得分最高
        sales = product.monthly_sales or 0
        if t.monthly_sales_max > t.monthly_sales_min:
            mid = (t.monthly_sales_min + t.monthly_sales_max) / 2
            span = (t.monthly_sales_max - t.monthly_sales_min) / 2
            scores["sales"] = round(max(0, 100 - abs(sales - mid) / span * 50), 1) if span else 50.0
        else:
            scores["sales"] = 50.0

        # 竞争度：垄断系数越低越高
        mono_values = [v for v in (product.listing_monopoly, product.brand_monopoly, product.seller_monopoly) if v is not None]
        if mono_values:
            avg_mono = sum(mono_values) / len(mono_values)
            scores["competition"] = round(max(0, 100 - avg_mono * 2), 1)
        else:
            scores["competition"] = 50.0

        # 利润空间：用价格作为代理（有价格且合理区间得分高），暂无拿货价时用中位数估算
        price = float(product.price) if product.price else 0
        if 10 <= price <= 50:
            scores["profit"] = 80.0
        elif price > 0:
            scores["profit"] = round(max(20, 100 - abs(price - 30) * 2), 1)
        else:
            scores["profit"] = 30.0

        # 新品活力
        new_ratio = product.new_product_ratio or 0
        scores["vitality"] = round(min(100, new_ratio * 10), 1)

        return scores

    def compute_comprehensive_score(self, breakdown: dict) -> float:
        """加权汇总各维度分数为综合评分。"""
        return round(sum(breakdown.get(k, 0) * w for k, w in SCORE_WEIGHTS.items()), 2)


# ---------- 配置加载 ----------

async def load_thresholds(db: AsyncSession) -> Thresholds:
    """从 system_configs 表读取 algorithm.thresholds。"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "algorithm.thresholds")
    )
    config = result.scalar_one_or_none()
    if config and config.config_value:
        return Thresholds.from_config(config.config_value)
    return Thresholds()


# 单例引擎
selection_engine = SelectionEngine()