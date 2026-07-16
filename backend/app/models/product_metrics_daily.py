"""product_metrics_daily 每日指标表模型。

对应数据库设计 4.1 表3。承载产品历史趋势（近 N 天销量/价格/评论数），支撑 FR-03 趋势分析。
"""

from datetime import date
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductMetricsDaily(Base):
    __tablename__ = "product_metrics_daily"
    __table_args__ = (
        UniqueConstraint("product_id", "metric_date", name="uq_metrics_product_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_sales: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    review_count: Mapped[Optional[int]] = mapped_column(Integer)