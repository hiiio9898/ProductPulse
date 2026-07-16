"""daily_reports 每日 AI 日报表模型。

对应数据库设计 4.1 表4。存储 GLM 生成的市场行情分析报告。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Date, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)

    # AI 生成内容（各模块）
    recommendations: Mapped[Optional[str]] = mapped_column(Text)
    trend_analysis: Mapped[Optional[str]] = mapped_column(Text)
    risk_alerts: Mapped[Optional[str]] = mapped_column(Text)
    action_suggestions: Mapped[Optional[str]] = mapped_column(Text)

    # 元数据
    model_used: Mapped[str] = mapped_column(String(50), default="glm-5.2")
    raw_prompt: Mapped[Optional[str]] = mapped_column(Text)  # 调试用，需脱敏
    generation_time_ms: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[date] = mapped_column(server_default=func.now())
    updated_at: Mapped[date] = mapped_column(server_default=func.now(), onupdate=func.now())