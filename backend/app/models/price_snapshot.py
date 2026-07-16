"""price_snapshots 价格快照表模型。

对应数据库设计 4.1 表2。记录 1688 拿货价与平台售价的历史快照（Phase 2 比价用，字段保留）。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)

    # 1688 价格信息
    price_1688: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    price_1688_previous: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    price_change_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    price_unit: Mapped[str] = mapped_column(String(20), default="per_kg")

    # 平台价格信息
    price_platform: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    price_platform_previous: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # 预估利润
    estimated_profit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    profit_margin: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[date] = mapped_column(server_default=func.now())