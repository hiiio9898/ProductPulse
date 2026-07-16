"""AI 适配层单元测试（mock，不依赖真实 GLM）。"""

from unittest.mock import patch, MagicMock
from app.adapters.ai_provider import AIProvider, AIResult, InsufficientBalanceError
from app.core.response import BizError


def make_provider(primary="glm-5.2", fallbacks=None):
    return AIProvider(api_key="fake-key", primary=primary, fallbacks=fallbacks or ["glm-4-flash"])


def test_chat_success_first_model():
    provider = make_provider()
    with patch.object(provider, "_call_single", return_value="日报内容"):
        result = provider.chat([{"role": "user", "content": "hi"}])
    assert result.success is True
    assert result.content == "日报内容"
    assert result.model_used == "glm-5.2"


def test_chat_fallback_on_insufficient_balance():
    """主力余额不足时自动切换备用模型。"""
    provider = make_provider(primary="glm-5.2", fallbacks=["glm-4-flash"])

    call_count = {"n": 0}

    def fake_call(model, messages, temperature, max_tokens):
        call_count["n"] += 1
        if model == "glm-5.2":
            raise InsufficientBalanceError("余额不足")
        return "备用模型生成的内容"

    with patch.object(provider, "_call_single", side_effect=fake_call):
        result = provider.chat([{"role": "user", "content": "hi"}])

    assert call_count["n"] == 2  # 调了两次
    assert result.success is True
    assert result.model_used == "glm-4-flash"
    assert result.content == "备用模型生成的内容"


def test_chat_all_models_fail():
    """所有模型都余额不足时返回失败结果。"""
    provider = make_provider(primary="glm-5.2", fallbacks=["glm-4-flash"])

    with patch.object(provider, "_call_single", side_effect=InsufficientBalanceError("余额不足")):
        result = provider.chat([{"role": "user", "content": "hi"}])

    assert result.success is False
    assert "余额不足" in (result.error or "")


def test_chat_no_api_key_raises():
    """无 API Key 时应抛 BizError。"""
    from unittest.mock import patch
    with patch("app.adapters.ai_provider.settings") as mock_settings:
        mock_settings.glm_api_key = ""
        mock_settings.glm_model_primary = "glm-4-flash"
        mock_settings.glm_model_fallback = "glm-4-flash"
        provider = AIProvider()
        provider.api_key = ""
        try:
            provider.chat([{"role": "user", "content": "hi"}])
            assert False, "应抛 BizError"
        except BizError as e:
            assert "Key 未配置" in e.message


def test_model_chain_dedup():
    """模型链去重，主力不重复出现在 fallbacks。"""
    provider = make_provider(primary="glm-5.2", fallbacks=["glm-5.2", "glm-4-flash"])
    chain = provider._model_chain()
    assert chain == ["glm-5.2", "glm-4-flash"]


def test_prompt_split_sections():
    """日报 Markdown 按 ## 标题分模块。"""
    from app.tasks.generate_report import _split_sections
    md = """## 今日推荐
推荐A
推荐B
## 趋势解读
趋势内容
## 风险提示
风险A
## 行动建议
建议1"""
    sections = _split_sections(md)
    assert "今日推荐" in sections
    assert "推荐A" in sections["今日推荐"]
    assert "行动建议" in sections
    assert "建议1" in sections["行动建议"]