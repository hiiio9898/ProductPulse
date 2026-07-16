"""Sorftime 数据同步服务。

把 Sorftime ProductSearch 返回的产品数据写入/更新 products 表，
并记录每日指标到 product_metrics_daily。
"""

from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.sorftime import sorftime_adapter, ProductListItem
from app.models.product import Product
from app.models.product_metrics_daily import ProductMetricsDaily


async def upsert_product(db: AsyncSession, item: ProductListItem, data_date: date,
                         category: Optional[str] = None) -> Product:
    """根据 sorftime_id 更新或创建产品记录。"""
    result = await db.execute(
        select(Product).where(Product.sorftime_id == item.asin)
    )
    product = result.scalar_one_or_none()

    if product is None:
        product = Product(sorftime_id=item.asin, title=item.title or "", data_date=data_date)
        db.add(product)

    # 更新字段
    product.title = item.title or product.title
    product.category = category or product.category
    product.monthly_sales = item.monthly_sales
    product.price = item.price
    product.review_count = item.ratings_count
    product.data_date = data_date
    product.deleted_at = None  # 恢复软删除

    await db.flush()
    return product


async def record_daily_metrics(db: AsyncSession, product_id: int, metric_date: date,
                               monthly_sales: Optional[int], price: Optional[float],
                               review_count: Optional[int]) -> None:
    """记录当日指标（存在则更新，靠唯一约束防重）。"""
    result = await db.execute(
        select(ProductMetricsDaily).where(
            ProductMetricsDaily.product_id == product_id,
            ProductMetricsDaily.metric_date == metric_date,
        )
    )
    metric = result.scalar_one_or_none()
    if metric is None:
        metric = ProductMetricsDaily(
            product_id=product_id, metric_date=metric_date,
            monthly_sales=monthly_sales, price=price, review_count=review_count,
        )
        db.add(metric)
    else:
        metric.monthly_sales = monthly_sales
        metric.price = price
        metric.review_count = review_count