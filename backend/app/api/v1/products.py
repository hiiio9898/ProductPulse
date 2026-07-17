"""选品中心 API。

GET /api/v1/products/          - 产品列表（筛选+排序+分页）
GET /api/v1/products/{id}      - 产品详情
GET /api/v1/products/recommendations/weekly - 本周推荐清单
POST /api/v1/products/sync     - 手动触发 Sorftime 同步
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import BizError, ErrorCode, ok_response
from app.core.security import AuthRequired
from app.models.product import Product
from app.models.recommendation import Recommendation

router = APIRouter(tags=["products"])


@router.get("/products/")
async def list_products(
    platform: str | None = Query(default=None, pattern="^(amazon|tiktok)$"),
    site: str | None = Query(default=None),
    category: str | None = Query(default=None),
    match_status: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    sort_by: str = Query(default="score", pattern="^(score|price|sales)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: bool = AuthRequired,
):
    """获取产品列表，支持多条件筛选与排序。"""
    query = select(Product).where(Product.deleted_at.is_(None))

    if platform:
        query = query.where(Product.platform == platform)
    if category:
        query = query.where(Product.category == category)
    if match_status:
        query = query.where(Product.match_status == match_status)
    if min_score is not None:
        query = query.where(Product.comprehensive_score >= min_score)

    # 排序
    sort_map = {"score": Product.comprehensive_score, "price": Product.price, "sales": Product.monthly_sales}
    col = sort_map[sort_by]
    query = query.order_by(col.desc() if sort_order == "desc" else col.asc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    products = db.execute(query).scalars().all()

    items = [
        {
            "id": p.id,
            "sorftime_id": p.sorftime_id,
            "title": p.title,
            "platform": p.platform,
            "category": p.category,
            "monthly_sales": p.monthly_sales,
            "price": float(p.price) if p.price else None,
            "review_count": p.review_count,
            "comprehensive_score": float(p.comprehensive_score) if p.comprehensive_score else None,
            "risk_tags": p.risk_tags,
            "match_status": p.match_status,
            "data_date": str(p.data_date) if p.data_date else None,
        }
        for p in products
    ]
    return ok_response({"items": items, "page": page, "page_size": page_size})


@router.get("/products/{product_id}")
async def get_product(product_id: int, db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取单个产品详情。"""
    product = db.get(Product, product_id)
    if not product or product.deleted_at:
        raise BizError(ErrorCode.NOT_FOUND, "产品不存在")
    return ok_response(data={
        "id": product.id,
        "sorftime_id": product.sorftime_id,
        "title": product.title,
        "category": product.category,
        "platform": product.platform,
        "monthly_sales": product.monthly_sales,
        "price": float(product.price) if product.price else None,
        "listing_monopoly": float(product.listing_monopoly) if product.listing_monopoly else None,
        "brand_monopoly": float(product.brand_monopoly) if product.brand_monopoly else None,
        "seller_monopoly": float(product.seller_monopoly) if product.seller_monopoly else None,
        "review_count": product.review_count,
        "new_product_ratio": float(product.new_product_ratio) if product.new_product_ratio else None,
        "seller_count": product.seller_count,
        "amazon_self_ratio": float(product.amazon_self_ratio) if product.amazon_self_ratio else None,
        "comprehensive_score": float(product.comprehensive_score) if product.comprehensive_score else None,
        "risk_tags": product.risk_tags,
        "match_status": product.match_status,
        "data_date": str(product.data_date) if product.data_date else None,
    })


@router.get("/products/recommendations/weekly")
async def weekly_recommendations(db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取本周推荐清单 TOP 10。"""
    from datetime import timedelta
    week_start = date.today() - timedelta(days=date.today().weekday())

    rows = db.execute(
        select(Recommendation, Product)
        .join(Product, Recommendation.product_id == Product.id)
        .where(Recommendation.week_start == week_start, Product.deleted_at.is_(None))
        .order_by(Recommendation.rank_position)
        .limit(10)
    ).all()

    items = [
        {
            "rank": rec.rank_position,
            "product_id": product.id,
            "title": product.title,
            "category": product.category,
            "score": float(product.comprehensive_score) if product.comprehensive_score else None,
            "reason": rec.reason,
            "expected_daily_orders": rec.expected_daily_orders,
        }
        for rec, product in rows
    ]
    return ok_response({"items": items, "week_start": str(week_start)})


@router.post("/products/sync")
async def trigger_sync(
    platform: str = Query(default="tiktok", pattern="^(amazon|tiktok)$"),
    site: str = Query(default="US"),
    category: str | None = Query(default=None),
    _: bool = AuthRequired,
):
    """手动触发数据同步（异步任务）。

    platform: amazon 或 tiktok
    site: 站点代码（Amazon: US/JP/DE..., TikTok: US/JP/GB...）
    category: 可选，指定单个品类（不传则同步默认品类）
    """
    from app.tasks.sync_sorftime import sync_sorftime_daily, DEFAULT_CATEGORIES
    cats = [category] if category else DEFAULT_CATEGORIES
    task = sync_sorftime_daily.delay(categories=cats, platform=platform, site=site)
    return ok_response(data={"task_id": task.id, "status": "queued", "platform": platform, "site": site})