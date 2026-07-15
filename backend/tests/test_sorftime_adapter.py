"""Sorftime Standard API 适配层单元测试。

通过 monkeypatch 模拟 _call 返回值，验证解析逻辑。不依赖真实 SK 与网络。
返回字段为 Sorftime 真实的 PascalCase 格式。
"""

from app.adapters.sorftime import SorftimeAdapter, AMAZON_DOMAIN_MAP, ALI1688_DOMAIN
from app.core.response import BizError, ErrorCode


def make_adapter():
    return SorftimeAdapter(sk="fake-sk", base_url="https://mock.sorftime.com/api", redis_client=None)


def test_domain_mapping():
    assert AMAZON_DOMAIN_MAP["US"] == 1
    assert AMAZON_DOMAIN_MAP["JP"] == 7
    assert ALI1688_DOMAIN == 601


def test_unsupported_site_raises():
    adapter = make_adapter()
    try:
        adapter._domain("XX")
        assert False, "应抛 BizError"
    except BizError as e:
        assert e.code == ErrorCode.PARAM_INVALID


def test_product_detail():
    adapter = make_adapter()
    adapter._call = lambda endpoint, domain, params, use_cache=True: {"Code": 0, "Data": {
        "Asin": "B0XXX", "Title": "Test", "Price": 14.97,
        "Ratings": 4.8, "RatingsCount": 38970, "AsinSalesCount": 160042,
        "Profit": 7.83, "ProfitRate": 52.30, "APlus": True,
    }}
    d = adapter.product_detail("US", "B0XXX")
    assert d.asin == "B0XXX"
    assert d.price == 14.97
    assert d.rating == 4.8
    assert d.monthly_sales == 160042
    assert d.aplus is True


def test_product_detail_calls_correct_endpoint_and_domain():
    adapter = make_adapter()
    captured = {}

    def fake_call(endpoint, domain, params, use_cache=True):
        captured.update(endpoint=endpoint, domain=domain, params=params)
        return {"Code": 0, "Data": {"Asin": "B0XXX"}}

    adapter._call = fake_call
    adapter.product_detail("DE", "B0XXX", trend=2)
    assert captured["endpoint"] == "ProductRequest"
    assert captured["domain"] == 3  # DE
    assert captured["params"]["trend"] == 2


def test_product_search():
    adapter = make_adapter()
    adapter._call = lambda endpoint, domain, params, use_cache=True: {"Code": 0, "Data": {
        "Products": [
            {"Asin": "B0A", "Title": "A", "Price": 9.99, "AsinSalesCount": 500, "PotentialIndex": 14.96, "APlus": True},
            {"Asin": "B0B", "Title": "B", "Price": 19.99, "AsinSalesCount": 200},
        ]
    }}
    items = adapter.product_search("US", nodeId="3743561", priceRangeMin=10)
    assert len(items) == 2
    assert items[0].asin == "B0A"
    assert items[0].potential_index == 14.96


def test_asin_sales_volume():
    adapter = make_adapter()
    adapter._call = lambda endpoint, domain, params, use_cache=True: {"Code": 0, "Data": [
        ["2024-05-01", 98211, 2],
        ["2024-06-01", 174202, 2],
    ]}
    result = adapter.asin_sales_volume("US", "B0XXX")
    assert len(result) == 2
    assert result[0] == {"date": "2024-05-01", "sales": 98211, "type": 2}


def test_product_reviews_query():
    adapter = make_adapter()
    adapter._call = lambda endpoint, domain, params, use_cache=True: {"Code": 0, "Data": [
        {"Attribute": "Style=4", "Date": "20260504", "Rating": 5.0, "Title": "Great", "Content": "Works well"},
    ]}
    reviews = adapter.product_reviews_query("US", "B0XXX")
    assert len(reviews) == 1
    assert reviews[0].rating == 5.0


def test_ali1688_search():
    """1688 查询应使用 domain=601。"""
    adapter = make_adapter()
    captured = {}

    def fake_call(endpoint, domain, params, use_cache=True):
        captured.update(endpoint=endpoint, domain=domain)
        return {"Code": 0, "Data": [
            {"Title": "PLA 耗材 1kg", "Price": 25.0, "SalesOf30d": 1000, "StoreName": "工厂A"},
        ]}

    adapter._call = fake_call
    result = adapter.ali1688_search("3D打印耗材")
    assert captured["endpoint"] == "ProductSearchFromName"
    assert captured["domain"] == 601
    assert len(result) == 1
    assert result[0]["Title"] == "PLA 耗材 1kg"


def test_missing_sk_raises_biz_error():
    adapter = SorftimeAdapter(sk="", base_url="https://mock", redis_client=None)
    try:
        adapter.product_detail("US", "B0XXX")
        assert False, "应抛 BizError"
    except BizError as e:
        assert e.code == ErrorCode.API_FAILED


def test_get_helper_case_insensitive():
    """_g 应大小写兼容取值。"""
    d = {"Asin": "B0X", "Title": "T"}
    assert SorftimeAdapter._g(d, "Asin") == "B0X"
    assert SorftimeAdapter._g(d, "asin") == "B0X"
    assert SorftimeAdapter._g(d, "Missing") is None