"""比价监控 API（FR-02）。

POST /api/v1/price/match/{product_id}  - 手动匹配产品与 1688 商品
POST /api/v1/price/refresh-all         - 手动刷新所有关联产品价格
GET  /api/v1/price/alerts              - 获取当前价格预警
GET  /api/v1/price/check/{product_id}  - 获取某产品最新价格快照
PUT  /api/v1/price/confirm/{product_id} - 确认/拒绝 1688 关联
"""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import BizError, ErrorCode, ok_response
from app.core.security import AuthRequired
from app.models.product import Product
from app.models.price_snapshot import PriceSnapshot
from app.services.price_compare import price_compare_service, MatchResult

router = APIRouter(tags=["price"])


class MatchConfirm(BaseModel):
    """确认关联请求体。"""

    source_id: str           # 1688 ProductId
    source_title: str        # 1688 标题
    match_status: str        # confirmed / rejected
    price_cny: float | None = None


# ---------- 手动匹配 ----------

@router.post("/price/match/{product_id}")
async def match_product(product_id: int, db: Session = Depends(get_db), _: bool = AuthRequired):
    """手动触发产品与 1688 商品的匹配，返回 Top3 候选供人工确认。"""
    product = db.get(Product, product_id)
    if not product or product.deleted_at:
        raise BizError(ErrorCode.NOT_FOUND, "产品不存在")

    matches = price_compare_service.search_1688(product.title, top_n=3)
    return ok_response(data={
        "product_id": product_id,
        "candidates": [
            {
                "source_id": m.source_id,
                "title": m.title,
                "price_cny": m.price_cny,
                "price_usd": m.price_usd,
                "sales_30d": m.sales_30d,
                "store_name": m.store_name,
                "similarity": m.similarity,
            }
            for m in matches
        ],
    })


@router.put("/price/confirm/{product_id}")
async def confirm_match(product_id: int, body: MatchConfirm, db: Session = Depends(get_db), _: bool = AuthRequired):
    """确认或拒绝 1688 关联。"""
    product = db.get(Product, product_id)
    if not product or product.deleted_at:
        raise BizError(ErrorCode.NOT_FOUND, "产品不存在")

    if body.match_status == "confirmed":
        product.matched_1688_id = body.source_id
        product.matched_1688_title = body.source_title
        product.match_status = "confirmed"
        if body.price_cny:
            product.match_confidence = 100.0
    elif body.match_status == "rejected":
        product.match_status = "rejected"

    db.commit()
    return ok_response(data={
        "product_id": product_id,
        "match_status": product.match_status,
        "matched_1688_id": product.matched_1688_id,
    }, message="关联状态已更新")


# ---------- 价格检查 ----------

@router.get("/price/check/{product_id}")
async def check_price(product_id: int, db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取某产品最新价格快照。"""
    product = db.get(Product, product_id)
    if not product or product.deleted_at:
        raise BizError(ErrorCode.NOT_FOUND, "产品不存在")

    snapshot = db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .order_by(PriceSnapshot.snapshot_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not snapshot:
        return ok_response(data=None, message="暂无价格快照")

    alert = price_compare_service.check_alert(snapshot.price_change_percent)

    return ok_response(data={
        "product_id": product_id,
        "price_1688": float(snapshot.price_1688) if snapshot.price_1688 else None,
        "price_1688_previous": float(snapshot.price_1688_previous) if snapshot.price_1688_previous else None,
        "price_change_percent": float(snapshot.price_change_percent) if snapshot.price_change_percent else None,
        "price_platform": float(snapshot.price_platform) if snapshot.price_platform else None,
        "estimated_profit": float(snapshot.estimated_profit) if snapshot.estimated_profit else None,
        "profit_margin": float(snapshot.profit_margin) if snapshot.profit_margin else None,
        "snapshot_date": str(snapshot.snapshot_date),
        "alert": alert,
    })


@router.post("/price/refresh-all")
async def refresh_all(_: bool = AuthRequired):
    """手动刷新所有关联产品价格（异步任务）。"""
    from app.tasks.sync_1688 import sync_1688_prices
    task = sync_1688_prices.delay()
    return ok_response(data={"task_id": task.id, "status": "queued"})


# ---------- 预警列表 ----------

@router.get("/price/alerts")
async def price_alerts(db: Session = Depends(get_db), _: bool = AuthRequired):
    """获取当前所有价格预警（变动 >= 5% 的最近快照）。"""
    # 取每个产品最近一次快照，筛选有变动的
    products = db.execute(
        select(Product).where(
            Product.deleted_at.is_(None),
            Product.match_status == "confirmed",
        )
    ).scalars().all()

    alerts = []
    for product in products:
        snapshot = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product.id)
            .order_by(PriceSnapshot.snapshot_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if snapshot and snapshot.price_change_percent is not None:
            alert = price_compare_service.check_alert(snapshot.price_change_percent)
            if alert:
                alerts.append({
                    "product_id": product.id,
                    "title": product.title,
                    "price_change_percent": float(snapshot.price_change_percent),
                    "price_1688": float(snapshot.price_1688) if snapshot.price_1688 else None,
                    "alert": alert,
                    "snapshot_date": str(snapshot.snapshot_date),
                })

    return ok_response({"items": alerts, "total": len(alerts)})