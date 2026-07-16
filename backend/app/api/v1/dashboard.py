"""看板首页概览 API。

GET /api/v1/dashboard/overview - 今日推荐数、预警数、待匹配数、TOP1 评分
GET /api/v1/dashboard/trends   - 近 7 天品类趋势
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok_response
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.core.security import AuthRequired

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/overview")
async def dashboard_overview(db: Session = Depends(get_db), _: bool = AuthRequired):
    """看板首页数据汇总（4 个 KPI 卡片）。"""
    today = date.today()

    # 今日推荐数（本周 recommendations）
    week_start = today - timedelta(days=today.weekday())
    rec_count = db.execute(
        select(func.count(Recommendation.id)).where(Recommendation.week_start == week_start)
    ).scalar() or 0

    # 预警数量（risk_tags 非空的产品）
    alert_count = db.execute(
        select(func.count(Product.id)).where(
            Product.risk_tags.isnot(None),
            Product.deleted_at.is_(None),
        )
    ).scalar() or 0

    # 待匹配 SKU（match_status=pending）
    pending_count = db.execute(
        select(func.count(Product.id)).where(
            Product.match_status == "pending",
            Product.deleted_at.is_(None),
        )
    ).scalar() or 0

    # 综合评分 TOP1
    top_product = db.execute(
        select(Product).where(Product.deleted_at.is_(None))
        .order_by(Product.comprehensive_score.desc()).limit(1)
    ).scalar_one_or_none()

    data = {
        "recommendations_today": rec_count,
        "alerts_count": alert_count,
        "pending_sku_count": pending_count,
        "top_score": float(top_product.comprehensive_score) if top_product and top_product.comprehensive_score else 0,
        "top_product_title": top_product.title if top_product else None,
    }
    return ok_response(data)


@router.get("/dashboard/trends")
async def dashboard_trends(db: Session = Depends(get_db), _: bool = AuthRequired):
    """近 7 天数据趋势（按 data_date 汇总产品数与平均销量）。"""
    start = date.today() - timedelta(days=7)
    rows = db.execute(
        select(
            Product.data_date,
            func.count(Product.id).label("product_count"),
            func.avg(Product.monthly_sales).label("avg_sales"),
        )
        .where(Product.data_date >= start, Product.deleted_at.is_(None))
        .group_by(Product.data_date)
        .order_by(Product.data_date)
    ).all()

    data = [
        {
            "date": str(row.data_date),
            "product_count": row.product_count,
            "avg_sales": round(float(row.avg_sales), 1) if row.avg_sales else 0,
        }
        for row in rows
    ]
    return ok_response(data)