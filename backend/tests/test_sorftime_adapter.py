"""Sorftime 适配层单元测试。

通过 monkeypatch 模拟 _call 返回值，验证各接口的容错解析逻辑正确。
不依赖真实 API Key 与网络。
"""

import json

from app.adapters.sorftime import SorftimeAdapter, _parse_lenient, _to_float, _to_int


def make_adapter():
    """构造一个不走真实网络的适配器（无 Key 也不影响 _call 被 mock）。"""
    return SorftimeAdapter(api_key="fake", base_url="https://mock.sorftime.com", redis_client=None)


def test_parse_lenient_dict():
    assert _parse_lenient({"a": 1}) == {"a": 1}


def test_parse_lenient_json_string():
    assert _parse_lenient('{"a": 1}') == {"a": 1}


def test_parse_lenient_embedded_json():
    raw = '前导文字 [{"k": "v"}] 尾部文字'
    assert _parse_lenient(raw) == [{"k": "v"}]


def test_parse_lenient_garbage_returns_original():
    raw = "完全不是 JSON 的纯文本"
    assert _parse_lenient(raw) == raw


def test_to_float_strips_units():
    assert _to_float("12.5%") == 12.5
    assert _to_int("1,600") == 1600
    assert _to_float(None) is None


def test_similar_product_feature(adapter=None):
    adapter = adapter or make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": json.dumps([
        {"产品特点": "不粘涂层", "产品数量占比": "占比82.35%", "月销量占比": "占比67.47%", "产品特点说明": "易清洁"},
    ])}
    result = adapter.similar_product_feature("US", "air fryer")
    assert len(result) == 1
    assert result[0].feature == "不粘涂层"
    assert result[0].product_share == "占比82.35%"


def test_product_detail():
    adapter = make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": {
        "产品ASIN码": "B0XXX", "标题": "Test", "价格": 14.97,
        "星级": 4.8, "评论数": 38970, "月销量": "月销量：160042",
        "毛利": 7.83, "毛利率": 52.30, "APlus": True,
    }}
    detail = adapter.product_detail("US", "B0XXX")
    assert detail.asin == "B0XXX"
    assert detail.price == 14.97
    assert detail.rating == 4.8
    assert detail.monthly_sales == 160042
    assert detail.aplus is True


def test_product_variations_string_format():
    adapter = make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": [
        "子体：B0CTQDTF1V，属性：Style=6 Refill Cartridges，子体月销量：50000-60000",
    ]}
    variations = adapter.product_variations("US", "B0C3FTCYZL")
    assert len(variations) == 1
    assert variations[0].asin == "B0CTQDTF1V"
    assert variations[0].attribute == "Style=6 Refill Cartridges"
    assert variations[0].monthly_sales_range == "50000-60000"


def test_product_trend_string():
    adapter = make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": "2024年05月=98211,2024年06月=174202"}
    trend = adapter.product_trend("US", "B0XXX", "SalesVolume")
    assert len(trend) == 2
    assert trend[0] == {"date": "2024年05月", "value": 98211.0}


def test_product_reviews():
    adapter = make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": [
        {"评论产品的属性": "Style=4", "评论日期": "20260504", "评星": 5.0, "标题": "Great", "评论": "Works"},
    ]}
    reviews = adapter.product_reviews("US", "B0XXX", "Positive")
    assert len(reviews) == 1
    assert reviews[0].rating == 5.0


def test_product_search_list():
    adapter = make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": [
        {"产品ASIN码": "B0A", "标题": "A", "价格": 9.99, "月销量": 500, "产品潜力指数": 14.96, "APlus": True},
        {"产品ASIN码": "B0B", "标题": "B", "价格": 19.99, "月销量": 200},
    ]}
    items = adapter.product_search("US", searchName="test")
    assert len(items) == 2
    assert items[0].asin == "B0A"
    assert items[0].potential_index == 14.96
    assert items[0].aplus is True


def test_traffic_terms():
    adapter = make_adapter()
    adapter._call = lambda method, params, use_cache=True: {"data": [
        {"关键词": "fly trap", "月搜索量": 247203, "推荐竞价": "1.92", "曝光位置": "广告位,自然位"},
    ]}
    terms = adapter.product_traffic_terms("US", "B0XXX")
    assert terms[0].keyword == "fly trap"
    assert terms[0].monthly_search_volume == 247203


def test_competitor_keywords_uses_keyword_support_site():
    """competitor_product_keywords 的参数字段应为 keywordSupportSite。"""
    adapter = make_adapter()
    captured = {}

    def fake_call(method, params, use_cache=True):
        captured.update(params)
        return {"data": [{"关键词": "k", "关键词月搜索量": 100, "曝光位置": "第1页"}]}

    adapter._call = fake_call
    adapter.competitor_product_keywords("US", "B0XXX")
    assert "keywordSupportSite" in captured
    assert captured["keywordSupportSite"] == "US"


def test_customers_say_uses_site_field():
    """product_customers_say 的参数字段应为 site（非 amzSite）。"""
    adapter = make_adapter()
    captured = {}

    def fake_call(method, params, use_cache=True):
        captured.update(params)
        return {"data": {
            "产品ASIN码": "B0FX4C5HP1",
            "AI评论总结": "easy to install",
            "评论关键词分析": [
                {"关键词": "easy to install", "总提及次数": 156, "积极评论数": 142, "消极评论数": 14},
            ],
        }}

    adapter._call = fake_call
    result = adapter.product_customers_say("US", "B0FX4C5HP1")
    assert "site" in captured
    assert captured["site"] == "US"
    assert result.ai_summary == "easy to install"
    assert result.keywords[0].positive_count == 142


def test_missing_api_key_raises_biz_error():
    """无 Key 调用应抛 BizError(API_FAILED)，不向外抛原始网络异常。"""
    from app.core.response import BizError, ErrorCode
    adapter = SorftimeAdapter(api_key="", base_url="https://mock", redis_client=None)
    try:
        adapter.product_detail("US", "B0XXX")
        assert False, "应抛 BizError"
    except BizError as e:
        assert e.code == ErrorCode.API_FAILED