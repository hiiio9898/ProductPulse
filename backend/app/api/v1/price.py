"""比价监控 API（FR-02）。

POST /api/v1/price/match/{product_id}  - 手动匹配产品与 1688 商品
POST /api/v1/price/refresh-all         - 手动刷新所有关联产品价格
GET  /api/v1/price/alerts              - 获取当前价格预警
GET  /api/v1/price/check/{product_id}  - 获取某产品最新价格快照
PUT  /api/v1/price/confirm/{product_id} - 确认/拒绝 1688 关联
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
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




@router.get("/price/compare/{product_id}")
async def compare_product(
    product_id: int,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: bool = AuthRequired,
):
    """比价：优先返回最近一次缓存，force=true 强制刷新（消耗 API 额度）。"""
    product = db.get(Product, product_id)
    if not product or product.deleted_at:
        raise BizError(ErrorCode.NOT_FOUND, "Product not found")

    # 非强制刷新时，先查最近一次快照
    if not force:
        cached = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.product_id == product_id)
            .order_by(PriceSnapshot.snapshot_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if cached and cached.total_cost is not None:
            return ok_response(data=_snapshot_to_compare_dict(cached, product), message="cached")

    # 实时比价（消耗 API 额度）
    result = price_compare_service.compare(product, top_n=3)
    # 保存到数据库
    price_compare_service.record_snapshot(db, product, result, date.today())
    db.commit()

    data = {
        "product_id": product_id,
        "platform": product.platform,
        "exchange_rate": result.exchange_rate,
        "platform_price_usd": result.platform_price_usd,
        "platform_price_cny": result.platform_price_cny,
        "search_keyword_cn": result.search_keyword_cn,
        "best_match": None,
        "candidates": [],
        "cost_breakdown": None,
        "gross_profit_cny": result.gross_profit_cny,
        "gross_profit_usd": result.gross_profit_usd,
        "profit_margin": result.profit_margin,
    }

    if result.best_match:
        data["best_match"] = {
            "source_id": result.best_match.source_id,
            "title": result.best_match.title,
            "price_cny": result.best_match.price_cny,
            "price_usd": result.best_match.price_usd,
            "similarity": result.best_match.similarity,
            "store_name": result.best_match.store_name,
        }
        data["candidates"] = [
            {
                "source_id": m.source_id,
                "title": m.title,
                "price_cny": m.price_cny,
                "price_usd": m.price_usd,
                "similarity": m.similarity,
                "store_name": m.store_name,
            }
            for m in result.matches
        ]

    if result.cost:
        c = result.cost
        data["cost_breakdown"] = {
            "purchase_price": c.purchase_price,
            "international_shipping": c.international_shipping,
            "customs_duty": c.customs_duty,
            "platform_commission": c.platform_commission,
            "packaging": c.packaging,
            "return_loss": c.return_loss,
            "total_cost": c.total_cost,
            "total_cost_usd": c.total_cost_usd,
        }

    return ok_response(data=data)


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


def _snapshot_to_compare_dict(snap, product) -> dict:
    """把缓存的 PriceSnapshot 转为比价结果 dict（免消耗 API）。"""
    data = {
        "product_id": snap.product_id,
        "platform": product.platform,
        "exchange_rate": float(snap.exchange_rate) if snap.exchange_rate else None,
        "platform_price_usd": float(snap.price_platform) / float(snap.exchange_rate) if snap.price_platform and snap.exchange_rate else None,
        "platform_price_cny": float(snap.price_platform) if snap.price_platform else None,
        "search_keyword_cn": snap.search_keyword_cn or "",
        "best_match": None,
        "candidates": [],
        "cost_breakdown": None,
        "gross_profit_cny": None,
        "gross_profit_usd": float(snap.estimated_profit) if snap.estimated_profit else None,
        "profit_margin": float(snap.profit_margin) if snap.profit_margin else None,
        "snapshot_date": str(snap.snapshot_date),
        "cached": True,
    }
    if snap.matched_title:
        data["best_match"] = {
            "source_id": "",
            "title": snap.matched_title,
            "price_cny": float(snap.price_1688) if snap.price_1688 else None,
            "price_usd": round(float(snap.price_1688) / float(snap.exchange_rate), 2) if snap.price_1688 and snap.exchange_rate else None,
            "similarity": float(snap.similarity) if snap.similarity else None,
            "store_name": "",
        }
    if snap.total_cost:
        data["cost_breakdown"] = {
            "purchase_price": float(snap.price_1688) if snap.price_1688 else 0,
            "international_shipping": float(snap.cost_shipping) if snap.cost_shipping else 0,
            "customs_duty": float(snap.cost_customs) if snap.cost_customs else 0,
            "platform_commission": float(snap.cost_commission) if snap.cost_commission else 0,
            "packaging": float(snap.cost_packaging) if snap.cost_packaging else 0,
            "return_loss": float(snap.cost_return_loss) if snap.cost_return_loss else 0,
            "total_cost": float(snap.total_cost),
            "total_cost_usd": round(float(snap.total_cost) / float(snap.exchange_rate), 2) if snap.exchange_rate else None,
        }
        sell_cny = float(snap.price_platform) if snap.price_platform else 0
        data["gross_profit_cny"] = round(sell_cny - float(snap.total_cost), 2)
    return data
