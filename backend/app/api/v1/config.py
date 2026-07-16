"""配置中心 API。

GET    /api/v1/config                   - 获取所有系统配置
PUT    /api/v1/config/thresholds        - 更新选品阈值
PUT    /api/v1/config/ai-models         - 切换 AI 模型
GET    /api/v1/config/risk-rules        - 风险规则列表
POST   /api/v1/config/risk-rules        - 新增风险规则
PUT    /api/v1/config/risk-rules/{id}   - 更新风险规则
DELETE /api/v1/config/risk-rules/{id}   - 删除风险规则
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import BizError, ErrorCode, ok_response
from app.core.security import AuthRequired
from app.models.risk_rule import RiskRule
from app.models.system_config import SystemConfig

router = APIRouter(tags=["config"])


# ---------- 系统配置 ----------

@router.get("/config")
async def get_config(db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取所有系统配置。"""
    rows = db.execute(select(SystemConfig)).scalars().all()
    data = {row.config_key: row.config_value for row in rows}
    return ok_response(data)


class ThresholdUpdate(BaseModel):
    monthly_sales_min: int | None = None
    monthly_sales_max: int | None = None
    listing_monopoly: float | None = None
    brand_monopoly: float | None = None
    seller_monopoly: float | None = None
    new_product_ratio: float | None = None
    amazon_self_ratio: float | None = None


@router.put("/config/thresholds")
async def update_thresholds(body: ThresholdUpdate, db: Session = Depends(get_db), _: bool = AuthRequired):
    """更新选品阈值（合并已有值）。"""
    config = db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "algorithm.thresholds")
    ).scalar_one_or_none()
    if not config:
        raise BizError(ErrorCode.NOT_FOUND, "配置项不存在")

    current = dict(config.config_value)
    updates = body.model_dump(exclude_none=True)
    current.update(updates)
    config.config_value = current
    db.commit()
    return ok_response(data=current, message="阈值更新成功")


class AIModelUpdate(BaseModel):
    primary: str | None = None


@router.put("/config/ai-models")
async def update_ai_models(body: AIModelUpdate, db: Session = Depends(get_db), _: bool = AuthRequired):
    """切换 AI 主力模型。"""
    config = db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "ai.model_priority")
    ).scalar_one_or_none()
    if not config:
        raise BizError(ErrorCode.NOT_FOUND, "配置项不存在")

    current = dict(config.config_value)
    if body.primary:
        current["primary"] = body.primary
    config.config_value = current
    db.commit()
    return ok_response(data=current, message="模型切换成功")


# ---------- 风险规则 CRUD ----------

class RiskRuleCreate(BaseModel):
    rule_name: str
    trigger_conditions: dict
    risk_level: str = "warning"
    risk_tag: str | None = None
    alert_message: str | None = None
    suggested_action: str | None = None


class RiskRuleUpdate(BaseModel):
    rule_name: str | None = None
    trigger_conditions: dict | None = None
    risk_level: str | None = None
    risk_tag: str | None = None
    alert_message: str | None = None
    suggested_action: str | None = None
    is_active: bool | None = None


def _rule_to_dict(rule: RiskRule) -> dict:
    return {
        "id": rule.id,
        "rule_name": rule.rule_name,
        "trigger_conditions": rule.trigger_conditions,
        "risk_level": rule.risk_level,
        "risk_tag": rule.risk_tag,
        "alert_message": rule.alert_message,
        "suggested_action": rule.suggested_action,
        "is_active": rule.is_active,
        "created_at": str(rule.created_at) if rule.created_at else None,
    }


@router.get("/config/risk-rules")
async def list_risk_rules(db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取风险规则列表。"""
    rules = db.execute(select(RiskRule).order_by(RiskRule.id)).scalars().all()
    return ok_response({"items": [_rule_to_dict(r) for r in rules]})


@router.post("/config/risk-rules")
async def create_risk_rule(body: RiskRuleCreate, db: Session = Depends(get_db), _: bool = AuthRequired):
    """新增风险规则。"""
    rule = RiskRule(
        rule_name=body.rule_name,
        trigger_conditions=body.trigger_conditions,
        risk_level=body.risk_level,
        risk_tag=body.risk_tag,
        alert_message=body.alert_message,
        suggested_action=body.suggested_action,
        created_by="admin",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return ok_response(data=_rule_to_dict(rule), message="规则创建成功")


@router.put("/config/risk-rules/{rule_id}")
async def update_risk_rule(rule_id: int, body: RiskRuleUpdate, db: Session = Depends(get_db), _: bool = AuthRequired):
    """更新风险规则。"""
    rule = db.get(RiskRule, rule_id)
    if not rule:
        raise BizError(ErrorCode.NOT_FOUND, "规则不存在")

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return ok_response(data=_rule_to_dict(rule), message="规则更新成功")


@router.delete("/config/risk-rules/{rule_id}")
async def delete_risk_rule(rule_id: int, db: Session = Depends(get_db), _: bool = AuthRequired):
    """删除风险规则。"""
    rule = db.get(RiskRule, rule_id)
    if not rule:
        raise BizError(ErrorCode.NOT_FOUND, "规则不存在")
    db.delete(rule)
    db.commit()
    return ok_response(message="规则已删除")