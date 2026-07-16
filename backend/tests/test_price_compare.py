"""比价服务单元测试（逻辑层，1688 调用 mock）。"""

from datetime import date
from unittest.mock import patch

from app.services.price_compare import PriceCompareService, PRICE_CHANGE_ALERT_THRESHOLD
from app.models.product import Product
from app.models.price_snapshot import PriceSnapshot


def make_product(**kwargs):
    defaults = dict(
        sorftime_id="B0TEST", title="PLA 3D Printer Filament 1.75mm Black 1kg",
        category="3D printer filament", monthly_sales=80000, price=22.99,
        match_status="pending", data_date=date(2026, 7, 16),
    )
    defaults.update(kwargs)
    return Product(**defaults)


def test_extract_keyword():
    svc = PriceCompareService()
    kw = svc._extract_keyword("iRobot Official Roomba Vacuum Cleaner for Home")
    assert "Official" not in kw  # 噪音词被过滤
    assert len(kw) > 0


def test_similarity_identical():
    svc = PriceCompareService()
    assert svc._similarity("PLA filament black", "PLA filament black") == 100.0


def test_similarity_partial():
    svc = PriceCompareService()
    sim = svc._similarity("PLA filament 1.75mm", "PLA filament 1kg black")
    assert 0 < sim < 100


def test_similarity_no_overlap():
    svc = PriceCompareService()
    assert svc._similarity("PLA filament", "ink cartridge epson") == 0.0


def test_check_alert_cost_up():
    svc = PriceCompareService()
    assert svc.check_alert(5.0) == "cost_alert"
    assert svc.check_alert(10.0) == "cost_alert"


def test_check_alert_price_drop():
    svc = PriceCompareService()
    assert svc.check_alert(-5.0) == "price_drop"
    assert svc.check_alert(-15.0) == "price_drop"


def test_check_alert_no_change():
    svc = PriceCompareService()
    assert svc.check_alert(2.0) is None
    assert svc.check_alert(-2.0) is None
    assert svc.check_alert(None) is None


def test_search_1688_returns_sorted_matches():
    """1688 查询结果按相似度降序。"""
    svc = PriceCompareService()
    mock_items = [
        {"Title": "PLA filament 1.75mm black 1kg", "Price": 36.0, "SalesOf30d": 100, "ProductId": "1688_1", "StoreName": "A厂"},
        {"Title": "PLA filament", "Price": 25.0, "SalesOf30d": 50, "ProductId": "1688_2", "StoreName": "B厂"},
        {"Title": "完全不相关的手机壳", "Price": 5.0, "SalesOf30d": 10, "ProductId": "1688_3", "StoreName": "C厂"},
    ]
    with patch.object(svc, "_extract_keyword", return_value="PLA filament"):
        with patch("app.services.price_compare.sorftime_adapter.ali1688_search", return_value=mock_items):
            matches = svc.search_1688("PLA 3D Printer Filament 1.75mm Black 1kg")

    assert len(matches) == 3
    # 相似度应降序
    assert matches[0].similarity >= matches[1].similarity >= matches[2].similarity
    # 价格换算正确
    assert matches[0].price_cny == 36.0


def test_compare_calculates_profit():
    svc = PriceCompareService()
    product = make_product(price=22.99)  # 平台售价 USD

    mock_match = [{"Title": "PLA filament black 1kg", "Price": 36.0, "SalesOf30d": 100, "ProductId": "1688_1", "StoreName": "A"}]
    with patch.object(svc, "_extract_keyword", return_value="PLA filament"):
        with patch("app.services.price_compare.sorftime_adapter.ali1688_search", return_value=mock_match):
            result = svc.compare(product)

    assert result.best_match is not None
    assert result.best_match.price_usd == 5.0  # 36 / 7.2
    # 利润 = 22.99 - 5.0 = 17.99
    assert result.estimated_profit_usd == 17.99


def test_alert_threshold_value():
    """确认预警阈值为 5%。"""
    assert PRICE_CHANGE_ALERT_THRESHOLD == 5.0