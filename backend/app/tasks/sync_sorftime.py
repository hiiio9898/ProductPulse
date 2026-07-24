"""Sorftime 数据同步定时任务。

每日 08:00（Asia/Shanghai）拉取指定品类的产品数据，
写入 products 表，记录每日指标，并跑选品算法 + 风险引擎更新评分与标签。
支持多平台（Amazon / TikTok）与多站点。
"""

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.adapters.sorftime import sorftime_adapter
from app.services.selection import SelectionEngine, load_thresholds
from app.services.risk_engine import RiskEngine, load_active_rules
from app.models.risk_rule import RiskRule

logger = get_logger("tasks.sync_sorftime")

# 默认同步的品类关键词
DEFAULT_CATEGORIES = ["3D printer filament", "sublimation ink", "photo paper"]

# 平台默认配置
PLATFORM_DEFAULTS = {
    "amazon": {"site": "US", "search_method": "product_search"},
    "tiktok": {"site": "US", "search_method": "tiktok_product_search"},
}


@celery_app.task(name="sync_sorftime_daily", bind=True)
def sync_sorftime_daily(
    self,
    categories: list[str] | None = None,
    platform: str = "amazon",
    site: str | None = None,
) -> dict:
    """每日同步产品数据。

    platform: "amazon" 或 "tiktok"
    site: 站点代码（Amazon: US/JP/DE..., TikTok: US/JP/GB...）
    categories: 要同步的品类关键词列表
    """
    cats = categories or DEFAULT_CATEGORIES
    pf = platform.lower()
    defaults = PLATFORM_DEFAULTS.get(pf, PLATFORM_DEFAULTS["amazon"])
    current_site = site or defaults["site"]

    today = date.today()
    logger.info(
        "数据同步开始",
        platform=pf, site=current_site, categories=cats, date=str(today),
    )

    db = SessionLocal()
    stats = {"synced": 0, "errors": 0, "categories": cats, "platform": pf, "site": current_site}

    try:
        thresholds = load_thresholds_sync(db)
        rules = load_active_rules_sync(db)
        engine = SelectionEngine(thresholds)
        risk = RiskEngine()

        for cat in cats:
            try:
                items = _fetch_products(pf, current_site, cat)
                logger.info("品类拉取完成", category=cat, platform=pf, count=len(items))

                for item in items:
                    try:
                        product = _upsert_product_sync_impl(db, item, today, category=cat, platform=pf, site=current_site)

                        record_daily_metrics_sync(
                            db, product.id, today,
                            item.monthly_sales, item.price, item.ratings_count,
                        )

                        result = engine.check_product(product, thresholds)
                        product.comprehensive_score = result.score

                        hits = risk.evaluate(product, rules)
                        product.risk_tags = risk.aggregate_tags(hits)

                        db.commit()
                        stats["synced"] += 1
                    except Exception as e:
                        db.rollback()
                        logger.warning("单条产品处理失败", sorftime_id=item.asin, error=str(e))
                        stats["errors"] += 1

            except Exception as e:
                logger.error("品类同步失败", category=cat, platform=pf, error=str(e))
                stats["errors"] += 1

        logger.info("数据同步完成", **stats)

        # 同步后自动为高分产品做 1688 匹配（所有平台，填充监控页数据）
        if stats["synced"] > 0:
            try:
                auto_match_count = _auto_match_1688(db, today, top_n=20)
                stats["auto_matched"] = auto_match_count
                logger.info("1688 自动匹配完成", matched=auto_match_count)
            except Exception as e:
                logger.warning("1688 自动匹配失败", error=str(e))
                stats["auto_matched"] = 0

        return stats

    finally:
        db.close()


def _auto_match_1688(db, data_date, top_n=20):
    """对高分产品自动匹配 1688 并生成价格快照。

    逻辑：取 Top N 未匹配的高分产品 -> 调 1688 搜索 ->
    取第一个候选自动确认 -> 记录快照。
    """
    from sqlalchemy import select
    from app.models.product import Product
    from app.services.price_compare import price_compare_service

    products = db.execute(
        select(Product).where(
            Product.deleted_at.is_(None),
            Product.match_status == "pending",
            Product.comprehensive_score.isnot(None),
        ).order_by(Product.comprehensive_score.desc()).limit(top_n)
    ).scalars().all()

    matched = 0
    for product in products:
        try:
            candidates = price_compare_service.search_1688(product.title, top_n=1)
            if not candidates:
                continue

            best = candidates[0]
            # 自动确认匹配
            product.matched_1688_id = best.source_id
            product.matched_1688_title = best.title
            product.match_status = "confirmed"
            product.match_confidence = best.similarity

            # 生成价格快照
            result = price_compare_service.compare(product)
            price_compare_service.record_snapshot(db, product, result, data_date)

            db.commit()
            matched += 1
        except Exception as e:
            db.rollback()
            logger.warning("1688 自动匹配单条失败", product_id=product.id, error=str(e))

    return matched


def _fetch_products(platform: str, site: str, keyword: str) -> list:
    """根据平台调用对应的 Sorftime 搜索接口。"""
    if platform == "tiktok":
        return sorftime_adapter.tiktok_product_search(site, name=keyword, page=1)
    # 默认 Amazon
    return sorftime_adapter.product_search(site, keyword=keyword, page=1)


# ---------- 同步版辅助（Celery 任务用同步 session） ----------

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


def _upsert_product_sync_impl(db, item, data_date, category=None, platform="amazon", site="US"):
    """同步版 upsert（直接复用同步 session）。"""
    from sqlalchemy import select
    from app.models.product import Product

    sorftime_id = item.asin or ""
    product = db.execute(
        select(Product).where(Product.sorftime_id == sorftime_id)
    ).scalar_one_or_none()

    if product is None:
        product = Product(sorftime_id=sorftime_id, title=item.title or "", data_date=data_date, platform=platform, site=site)
        db.add(product)

    product.title = item.title or product.title
    product.category = category or product.category
    product.platform = platform
    product.site = site
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
