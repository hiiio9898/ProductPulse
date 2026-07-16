"""1688 价格刷新定时任务（FR-02）。

每日 08:30（紧接 Sorftime 08:00 同步后）：
1. 取所有已确认关联 1688 的产品（match_status=confirmed）
2. 刷新 1688 拿货价，记录价格快照
3. 价格变动 >= 5% 触发预警，更新产品 risk_tags
"""

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.product import Product
from app.services.price_compare import price_compare_service

logger = get_logger("tasks.sync_1688")


@celery_app.task(name="sync_1688_prices", bind=True)
def sync_1688_prices(self) -> dict:
    """每日刷新已关联产品的 1688 价格。"""
    today = date.today()
    logger.info("1688 价格刷新开始", date=str(today))

    db = SessionLocal()
    stats = {"refreshed": 0, "alerts": 0, "errors": 0}

    try:
        # 取已确认关联的产品
        products = db.execute(
            __import__("sqlalchemy").select(Product).where(
                Product.match_status == "confirmed",
                Product.deleted_at.is_(None),
                Product.matched_1688_id.isnot(None),
            )
        ).scalars().all()

        logger.info("待刷新产品数", count=len(products))

        for product in products:
            try:
                result = price_compare_service.compare(product)
                snapshot = price_compare_service.record_snapshot(db, product, result, today)

                if snapshot and snapshot.price_change_percent is not None:
                    alert = price_compare_service.check_alert(snapshot.price_change_percent)
                    if alert:
                        # 更新产品风险标签
                        tag = "成本上涨预警" if alert == "cost_alert" else "降价利好"
                        tags = list(product.risk_tags or [])
                        if tag not in tags:
                            tags.append(tag)
                        product.risk_tags = tags
                        stats["alerts"] += 1
                        logger.warning("价格预警", product_id=product.id, change=snapshot.price_change_percent, alert=tag)

                db.commit()
                stats["refreshed"] += 1
            except Exception as e:
                db.rollback()
                logger.warning("单条刷新失败", product_id=product.id, error=str(e))
                stats["errors"] += 1

        logger.info("1688 价格刷新完成", **stats)
        return stats

    finally:
        db.close()