"""选品算法引擎与风险规则引擎单元测试。

纯逻辑测试，不依赖数据库。
"""

from app.services.selection import SelectionEngine, Thresholds, SCORE_WEIGHTS
from app.services.risk_engine import RiskEngine, RiskHit
from app.models.product import Product
from app.models.risk_rule import RiskRule


def _make_product(**kwargs):
    """构造测试产品，默认值通过所有通用阈值。"""
    defaults = dict(
        sorftime_id="B0TEST", title="Test Product", category="generic",
        monthly_sales=50000, price=25.0, listing_monopoly=20.0, brand_monopoly=30.0,
        seller_monopoly=30.0, review_count=100, new_product_ratio=8.0,
        seller_count=50, amazon_self_ratio=20.0,
    )
    defaults.update(kwargs)
    return Product(**defaults)


# ---------- 阈值过滤 ----------

def test_passes_all_thresholds():
    engine = SelectionEngine()
    result = engine.check_product(_make_product())
    assert result.passed is True
    assert len(result.fail_reasons) == 0
    assert result.score > 0


def test_fails_low_sales():
    engine = SelectionEngine()
    result = engine.check_product(_make_product(monthly_sales=100))
    assert result.passed is False
    assert any("月销量" in r for r in result.fail_reasons)


def test_fails_high_monopoly():
    engine = SelectionEngine()
    result = engine.check_product(_make_product(listing_monopoly=50.0))
    assert result.passed is False
    assert any("Listing垄断" in r for r in result.fail_reasons)


def test_fails_too_many_reviews():
    engine = SelectionEngine()
    result = engine.check_product(_make_product(review_count=500))
    assert result.passed is False
    assert any("评论数" in r for r in result.fail_reasons)


# ---------- 耗材特殊阈值 ----------

def test_filament_uses_special_thresholds():
    """3D 耗材品类应使用特殊阈值（销量下限 3000）。"""
    engine = SelectionEngine()
    # 通用阈值下 4000 会通过，但耗材特殊阈值下限也是 3000，应通过
    result = engine.check_product(_make_product(category="3D打印耗材", monthly_sales=4000, new_product_ratio=12.0))
    assert result.passed is True

    # 耗材评论上限 200，250 应不通过
    result2 = engine.check_product(_make_product(category="PLA filament", review_count=250))
    assert result2.passed is False


def test_non_filament_uses_general_thresholds():
    """非耗材品类用通用阈值（评论上限 300）。"""
    engine = SelectionEngine()
    result = engine.check_product(_make_product(category="ink", review_count=250))
    assert result.passed is True  # 250 < 300 通过


# ---------- 评分 ----------

def test_score_breakdown_has_all_dimensions():
    engine = SelectionEngine()
    result = engine.check_product(_make_product())
    for dim in ("sales", "competition", "profit", "vitality"):
        assert dim in result.score_breakdown
        assert 0 <= result.score_breakdown[dim] <= 100


def test_comprehensive_score_is_weighted():
    engine = SelectionEngine()
    result = engine.check_product(_make_product())
    expected = round(sum(result.score_breakdown[k] * w for k, w in SCORE_WEIGHTS.items()), 2)
    assert result.score == expected


def test_lower_monopoly_scores_higher_competition():
    engine = SelectionEngine()
    low_mono = engine.check_product(_make_product(listing_monopoly=10, brand_monopoly=10, seller_monopoly=10))
    high_mono = engine.check_product(_make_product(listing_monopoly=29, brand_monopoly=39, seller_monopoly=39))
    assert low_mono.score_breakdown["competition"] > high_mono.score_breakdown["competition"]


# ---------- 风险规则 ----------

def _make_rule(**kwargs):
    defaults = dict(
        rule_name="test", trigger_conditions={"category": "ink"},
        risk_level="warning", risk_tag="test_tag", alert_message="test alert",
        is_active=True,
    )
    defaults.update(kwargs)
    return RiskRule(**defaults)


def test_risk_category_match():
    engine = RiskEngine()
    product = _make_product(category="ink")
    rule = _make_rule(trigger_conditions={"category": "ink"})
    hits = engine.evaluate(product, [rule])
    assert len(hits) == 1
    assert hits[0].risk_tag == "test_tag"


def test_risk_category_no_match():
    engine = RiskEngine()
    product = _make_product(category="photo_paper")
    rule = _make_rule(trigger_conditions={"category": "ink"})
    hits = engine.evaluate(product, [rule])
    assert len(hits) == 0


def test_risk_review_count_threshold():
    engine = RiskEngine()
    product = _make_product(review_count=2000)
    rule = _make_rule(trigger_conditions={"review_count_min": 1000})
    hits = engine.evaluate(product, [rule])
    assert len(hits) == 1


def test_risk_inactive_rule_skipped():
    engine = RiskEngine()
    product = _make_product(category="ink")
    rule = _make_rule(is_active=False)
    hits = engine.evaluate(product, [rule])
    assert len(hits) == 0


def test_risk_worst_level():
    engine = RiskEngine()
    product = _make_product(category="ink", review_count=5000)
    rules = [
        _make_rule(rule_name="r1", risk_level="warning", trigger_conditions={"category": "ink"}),
        _make_rule(rule_name="r2", risk_level="danger", trigger_conditions={"review_count_min": 1000}),
    ]
    hits = engine.evaluate(product, rules)
    assert engine.worst_level(hits) == "danger"
    assert "test_tag" in engine.aggregate_tags(hits)