"""risk_rules 风险规则配置表模型。

对应数据库设计 4.1 表6。可配置的风险判定规则，含预置规则。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)

    risk_level: Mapped[str] = mapped_column(String(20), default="warning")
    risk_tag: Mapped[Optional[str]] = mapped_column(String(50))
    alert_message: Mapped[Optional[str]] = mapped_column(Text)
    suggested_action: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[date] = mapped_column(server_default=func.now())
    updated_at: Mapped[date] = mapped_column(server_default=func.now(), onupdate=func.now())