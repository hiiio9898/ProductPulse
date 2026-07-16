"""Sorftime 数据同步定时任务。

每日 08:00（Asia/Shanghai）拉取指定品类的 Sorftime 产品数据，
写入 products 表，记录每日指标，并跑选品算法 + 风险引擎更新评分与标签。
"""

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.adapters.sorftime import sorftime_adapter
from app.services.product_sync import upsert_product, record_daily_metrics
from app.services.selection import SelectionEngine, load_thresholds
from app.services.risk_engine import RiskEngine, load_active_rules
from app.models.risk_rule import RiskRule

logger = get_logger("tasks.sync_sorftime")

# 默认同步的品类关键词
DEFAULT_CATEGORIES = ["3D printer filament", "sublimation ink", "photo paper"]


@celery_app.task(name="sync_sorftime_daily", bind=True)
def sync_sorftime_daily(self, categories: list[str] | None = None) -> dict:
    """每日同步 Sorftime 数据。

    同步流程：拉取 -> upsert products -> 记录 metrics -> 选品评分 -> 风险评估。
    """
    cats = categories or DEFAULT_CATEGORIES
    today = date.today()
    logger.info("Sorftime 每日同步开始", categories=cats, date=str(today))

    db = SessionLocal()
    stats = {"synced": 0, "errors": 0, "categories": cats}

    try:
        # 加载选品阈值与风险规则
        thresholds = load_thresholds_sync(db)
        rules = load_active_rules_sync(db)
        engine = SelectionEngine(thresholds)
        risk = RiskEngine()

        for cat in cats:
            try:
                items = sorftime_adapter.product_search(
                    "US",
                    keyword=cat,
                    page=1,
                )
                logger.info("品类拉取完成", category=cat, count=len(items))

                for item in items:
                    try:
                        product = upsert_product_sync(db, item, today, category=cat)

                        # 记录每日指标
                        record_daily_metrics_sync(
                            db, product.id, today,
                            item.monthly_sales, item.price, item.ratings_count,
                        )

                        # 选品评分
                        result = engine.check_product(product, thresholds)
                        product.comprehensive_score = result.score

                        # 风险评估
                        hits = risk.evaluate(product, rules)
                        product.risk_tags = risk.aggregate_tags(hits)

                        db.commit()
                        stats["synced"] += 1
                    except Exception as e:
                        db.rollback()
                        logger.warning("单条产品处理失败", asin=item.asin, error=str(e))
                        stats["errors"] += 1

            except Exception as e:
                logger.error("品类同步失败", category=cat, error=str(e))
                stats["errors"] += 1

        logger.info("Sorftime 每日同步完成", **stats)
        return stats

    finally:
        db.close()


# ---------- 同步版辅助（Celery 任务用同步 session） ----------
# 注意：services 层用 async 是为 FastAPI；Celery 任务用同步 wrapper

def load_thresholds_sync(db):
    from app.services.selection import Thresholds
    from app.models.system_config import SystemConfig
    from sqlalchemy import select

    config = db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "algorithm.thresholds")
    ).scalar_one_or_none()
    if config and config.config_value:
        return Thresholds.from_config(config.config_value)
    return Thresholds()


def load_active_rules_sync(db) -> list[RiskRule]:
    from sqlalchemy import select
    return list(db.execute(
        select(RiskRule).where(RiskRule.is_active.is_(True))
    ).scalars().all())


def upsert_product_sync(db, item, data_date, category=None):
    from app.services.product_sync import upsert_product
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        upsert_product(db, item, data_date, category)
    ) if False else _upsert_product_sync_impl(db, item, data_date, category)


def _upsert_product_sync_impl(db, item, data_date, category=None):
    """同步版 upsert（直接复用同步 session）。"""
    from sqlalchemy import select
    from app.models.product import Product

    product = db.execute(
        select(Product).where(Product.sorftime_id == item.asin)
    ).scalar_one_or_none()

    if product is None:
        product = Product(sorftime_id=item.asin, title=item.title or "", data_date=data_date)
        db.add(product)

    product.title = item.title or product.title
    product.category = category or product.category
    product.monthly_sales = item.monthly_sales
    product.price = item.price
    product.review_count = item.ratings_count
    product.data_date = data_date
    product.deleted_at = None
    db.flush()
    return product


def record_daily_metrics_sync(db, product_id, metric_date, monthly_sales, price, review_count):
    from sqlalchemy import select
    from app.models.product_metrics_daily import ProductMetricsDaily

    metric = db.execute(
        select(ProductMetricsDaily).where(
            ProductMetricsDaily.product_id == product_id,
            ProductMetricsDaily.metric_date == metric_date,
        )
    ).scalar_one_or_none()

    if metric is None:
        db.add(ProductMetricsDaily(
            product_id=product_id, metric_date=metric_date,
            monthly_sales=monthly_sales, price=price, review_count=review_count,
        ))
    else:
        metric.monthly_sales = monthly_sales
        metric.price = price
        metric.review_count = review_count