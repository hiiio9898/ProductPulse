"""recommendations 周度推荐清单表模型。

对应数据库设计 4.1 表5。选品算法输出的本周 TOP 推荐。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    rank_position: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    expected_daily_orders: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[date] = mapped_column(server_default=func.now())