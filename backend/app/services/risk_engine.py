"""风险规则引擎。

职责：根据 risk_rules 表中的规则，对产品打风险标签、生成预警。
规则结构（trigger_conditions JSONB）支持：
- {"category": "ink"}           品类匹配
- {"category": "ink", "type": "oil_based"} 品类+属性匹配
- {"review_count_min": 1000}    评论数阈值
- {"seller_count_max": 3}       卖家数阈值
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.risk_rule import RiskRule


class RiskHit:
    """单条规则命中结果。"""

    def __init__(self, rule_name: str, risk_level: str, risk_tag: str,
                 alert_message: str, suggested_action: Optional[str] = None):
        self.rule_name = rule_name
        self.risk_level = risk_level  # danger / warning / info
        self.risk_tag = risk_tag
        self.alert_message = alert_message
        self.suggested_action = suggested_action

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "risk_level": self.risk_level,
            "risk_tag": self.risk_tag,
            "alert_message": self.alert_message,
            "suggested_action": self.suggested_action,
        }


class RiskEngine:
    """风险规则引擎。"""

    @staticmethod
    def _matches(product: Product, conditions: dict) -> bool:
        """判断产品是否命中单条规则的全部条件。"""
        for key, expected in conditions.items():
            value = None
            if key == "category":
                value = (product.category or "").lower()
                if value != str(expected).lower():
                    return False
            elif key == "review_count_min":
                if (product.review_count or 0) < expected:
                    return False
            elif key == "review_count_max":
                if (product.review_count or 999999) > expected:
                    return False
            elif key == "seller_count_max":
                if (product.seller_count or 999999) > expected:
                    return False
            elif key == "seller_count_min":
                if (product.seller_count or 0) < expected:
                    return False
            elif key == "monthly_sales_max":
                if (product.monthly_sales or 0) > expected:
                    return False
            else:
                # 未知条件类型，不命中（避免误报）
                return False
        return True

    def evaluate(self, product: Product, rules: list[RiskRule]) -> list[RiskHit]:
        """对单个产品评估所有规则，返回命中的风险列表。"""
        hits: list[RiskHit] = []
        for rule in rules:
            if not rule.is_active:
                continue
            if self._matches(product, rule.trigger_conditions or {}):
                hits.append(RiskHit(
                    rule_name=rule.rule_name,
                    risk_level=rule.risk_level,
                    risk_tag=rule.risk_tag or "",
                    alert_message=rule.alert_message or "",
                    suggested_action=rule.suggested_action,
                ))
        return hits

    def aggregate_tags(self, hits: list[RiskHit]) -> list[str]:
        """把命中的风险汇总为标签数组（写入 product.risk_tags）。"""
        tags: list[str] = []
        for hit in hits:
            if hit.risk_tag and hit.risk_tag not in tags:
                tags.append(hit.risk_tag)
        return tags

    def worst_level(self, hits: list[RiskHit]) -> Optional[str]:
        """返回最严重的风险等级（danger > warning > info）。"""
        levels = [h.risk_level for h in hits]
        if "danger" in levels:
            return "danger"
        if "warning" in levels:
            return "warning"
        if "info" in levels:
            return "info"
        return None


async def load_active_rules(db: AsyncSession) -> list[RiskRule]:
    """加载所有启用的风险规则。"""
    result = await db.execute(
        select(RiskRule).where(RiskRule.is_active.is_(True))
    )
    return list(result.scalars().all())


# 单例
risk_engine = RiskEngine()