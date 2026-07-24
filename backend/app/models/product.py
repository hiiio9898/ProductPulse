"""products 产品主表模型。

对应数据库设计 4.1 表1。Sorftime 选品数据的核心存储。
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import Date, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sorftime_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    platform: Mapped[str] = mapped_column(String(20), default="amazon")
    site: Mapped[str] = mapped_column(String(10), default="US", index=True)

    # Sorftime 核心字段
    monthly_sales: Mapped[Optional[int]] = mapped_column(Integer)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    listing_monopoly: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    brand_monopoly: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    seller_monopoly: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    review_count: Mapped[Optional[int]] = mapped_column(Integer)
    new_product_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    seller_count: Mapped[Optional[int]] = mapped_column(Integer)
    amazon_self_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    # 1688 关联（Phase 2 暂缓，字段保留）
    matched_1688_id: Mapped[Optional[str]] = mapped_column(String(64))
    matched_1688_title: Mapped[Optional[str]] = mapped_column(String(500))
    match_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    match_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # 风险与评分
    risk_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    comprehensive_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), index=True)
    recommendation_reason: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳与软删除
    data_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[date] = mapped_column(server_default=func.now())
    updated_at: Mapped[date] = mapped_column(server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[date]] = mapped_column(Date)