"""selection / risk_engine / database 的 async 加载与 session 测试。"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.services.selection import load_thresholds, Thresholds, SelectionEngine
from app.services.risk_engine import load_active_rules, RiskEngine, RiskHit
from app.core.database import get_db, SessionLocal, engine
from app.core.config import settings
from app.models.product import Product
from app.models.system_config import SystemConfig
from app.models.risk_rule import RiskRule


# ---------- Thresholds ----------

def test_thresholds_from_config():
    t = Thresholds.from_config({"monthly_sales_min": 8000, "unknown_key": 1})
    assert t.monthly_sales_min == 8000
    # 未知 key 忽略，其余保持默认
    assert t.listing_monopoly == 30.0


def test_thresholds_for_category_non_filament():
    t = Thresholds()
    result = t.for_category("ink")
    assert result.monthly_sales_min == 5000  # 通用


def test_thresholds_for_category_filament_variants():
    """不同写法的耗材品类都识别为 filament。"""
    t = Thresholds()
    for cat in ["3D printer filament", "PLA filament", "3D打印耗材", "ABS打印"]:
        result = t.for_category(cat)
        assert result.monthly_sales_min == 3000, f"{cat} 应识别为耗材"


def test_load_thresholds_with_mock():
    """async load_thresholds 从 mock DB 读配置。"""
    mock_config = MagicMock()
    mock_config.config_value = {"monthly_sales_min": 7000}

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_config
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = asyncio.get_event_loop().run_until_complete(load_thresholds(mock_db))
    assert result.monthly_sales_min == 7000


def test_load_thresholds_fallback_default():
    """配置不存在时返回默认阈值。"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = asyncio.get_event_loop().run_until_complete(load_thresholds(mock_db))
    assert isinstance(result, Thresholds)
    assert result.monthly_sales_min == 5000


# ---------- RiskEngine async ----------

def test_load_active_rules_with_mock():
    mock_rule = MagicMock(spec=RiskRule)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_rule]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = asyncio.get_event_loop().run_until_complete(load_active_rules(mock_db))
    assert len(result) == 1


def test_risk_hit_to_dict():
    hit = RiskHit(rule_name="r", risk_level="danger", risk_tag="tag", alert_message="msg", suggested_action="act")
    d = hit.to_dict()
    assert d["rule_name"] == "r"
    assert d["suggested_action"] == "act"


def test_risk_engine_seller_count_conditions():
    """seller_count_max / seller_count_min 条件。"""
    engine = RiskEngine()
    product = MagicMock(spec=Product)
    product.seller_count = 2
    product.review_count = 100
    product.monthly_sales = 5000
    product.category = "ink"

    rule = MagicMock(spec=RiskRule)
    rule.is_active = True
    rule.trigger_conditions = {"seller_count_max": 3}
    rule.rule_name = "r"
    rule.risk_level = "warning"
    rule.risk_tag = "少卖家"
    rule.alert_message = "卖家少"
    rule.suggested_action = None

    hits = engine.evaluate(product, [rule])
    assert len(hits) == 1  # seller_count=2 <= 3 命中

    rule.trigger_conditions = {"seller_count_max": 1}
    hits = engine.evaluate(product, [rule])
    assert len(hits) == 0  # 2 > 1 不命中


def test_risk_engine_monthly_sales_max():
    engine = RiskEngine()
    product = MagicMock(spec=Product)
    product.monthly_sales = 200000
    product.review_count = 100
    product.category = "ink"
    product.seller_count = 10

    rule = MagicMock(spec=RiskRule)
    rule.is_active = True
    rule.trigger_conditions = {"monthly_sales_max": 300000}  # 200000 < 300000 才命中
    rule.rule_name = "r"
    rule.risk_level = "warning"
    rule.risk_tag = ""
    rule.alert_message = ""
    rule.suggested_action = None

    hits = engine.evaluate(product, [rule])
    assert len(hits) == 1


def test_risk_engine_unknown_condition_skipped():
    """未知条件类型不命中。"""
    engine = RiskEngine()
    product = MagicMock(spec=Product)
    product.category = "ink"
    rule = MagicMock(spec=RiskRule)
    rule.is_active = True
    rule.trigger_conditions = {"unknown_field": 1}
    rule.risk_tag = ""
    hits = engine.evaluate(product, [rule])
    assert len(hits) == 0


# ---------- database ----------

def test_get_db_yields_session():
    """get_db 依赖应返回可用 session 并自动关闭。"""
    gen = get_db()
    db = next(gen)
    assert db is not None
    # 能执行简单查询
    db.execute(SystemConfig.__table__.select().limit(1))
    gen.close()


def test_engine_configured():
    assert engine is not None
    assert "postgresql" in str(engine.url)