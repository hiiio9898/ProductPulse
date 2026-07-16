"""数据库初始化脚本。

在生产部署后执行，确保：
1. Alembic 迁移已应用（docker compose 启动时已自动跑）
2. 预置数据存在（风险规则、系统配置）
3. 管理员 token 已设置

用法：docker compose exec app python scripts/init_db.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.system_config import SystemConfig
from app.models.risk_rule import RiskRule
from app.core.logging import get_logger

logger = get_logger("scripts.init_db")

SEED_CONFIGS = [
    {
        "config_key": "ai.model_priority",
        "config_value": {"primary": settings.glm_model_primary, "backup": [settings.glm_model_fallback]},
        "description": "AI模型优先级",
    },
    {
        "config_key": "algorithm.thresholds",
        "config_value": {
            "monthly_sales_min": 5000, "monthly_sales_max": 150000,
            "listing_monopoly": 30, "brand_monopoly": 40, "seller_monopoly": 40,
            "new_product_ratio": 5, "amazon_self_ratio": 30, "review_count_max": 300,
        },
        "description": "选品阈值",
    },
]

SEED_RULES = [
    {
        "rule_name": "墨水-易燃液体",
        "trigger_conditions": {"category": "ink", "type": "oil_based"},
        "risk_level": "danger", "risk_tag": "易燃液体",
        "alert_message": "属3类易燃液体，需MSDS+非危鉴定，空运受限",
        "is_active": True, "created_by": "system",
    },
    {
        "rule_name": "相纸-易损",
        "trigger_conditions": {"category": "photo_paper"},
        "risk_level": "warning", "risk_tag": "易损易潮",
        "alert_message": "需三重包装+干燥剂，运输破损率高",
        "is_active": True, "created_by": "system",
    },
]


def init_db():
    db = SessionLocal()
    try:
        # 系统配置（upsert）
        for cfg in SEED_CONFIGS:
            existing = db.query(SystemConfig).filter_by(config_key=cfg["config_key"]).first()
            if existing:
                existing.config_value = cfg["config_value"]
            else:
                db.add(SystemConfig(**cfg))

        # 风险规则（跳过已存在的同名规则）
        for rule in SEED_RULES:
            existing = db.query(RiskRule).filter_by(rule_name=rule["rule_name"]).first()
            if not existing:
                db.add(RiskRule(**rule))

        db.commit()
        config_count = db.query(SystemConfig).count()
        rule_count = db.query(RiskRule).count()
        logger.info("数据库初始化完成", configs=config_count, rules=rule_count)
        print(f"[OK] 初始化完成: {config_count} 配置, {rule_count} 风险规则")
        print(f"[OK] 管理员 Token: {settings.app_secret_key[:8]}... (完整值见 .env APP_SECRET_KEY)")
    except Exception as e:
        db.rollback()
        logger.error("初始化失败", error=str(e))
        print(f"[FAIL] 初始化失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()