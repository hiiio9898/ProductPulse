"""AI 大模型适配层（FR-03）。

统一封装智谱 GLM 调用，支持：
- 主力模型自动降级到备用模型（GLM-5.2 → GLM-5.1 → glm-4-flash）
- 重试（tenacity 指数退避）+ 超时
- 余额不足(1113)/限流(429) 时自动切换备用模型
- 统一返回结构 + 耗时统计

外部 API 异常转为本系统错误码 2001/2002。
"""

import time
from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.core.response import BizError, ErrorCode

logger = get_logger("adapters.ai_provider")

GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_TIMEOUT = 60


@dataclass
class AIResult:
    """大模型调用结果。"""

    content: str
    model_used: str
    elapsed_ms: int
    success: bool
    error: Optional[str] = None


class InsufficientBalanceError(Exception):
    """余额不足或限流，应切换备用模型。"""


class AIProvider:
    """智谱 GLM 统一适配层。"""

    def __init__(self, api_key: Optional[str] = None,
                 primary: Optional[str] = None,
                 fallbacks: Optional[list[str]] = None):
        self.api_key = api_key or settings.glm_api_key
        self.primary = primary or settings.glm_model_primary
        self.fallbacks = fallbacks or self._load_fallbacks()

    @staticmethod
    def _load_fallbacks() -> list[str]:
        """从 system_configs 加载备用模型列表（兜底用默认）。"""
        defaults = ["glm-4-flash"]
        configured = settings.glm_model_fallback
        if configured and configured != settings.glm_model_primary:
            defaults.insert(0, configured)
        # 主力放最前，去重
        chain = [settings.glm_model_primary] + defaults
        seen = set()
        return [m for m in chain if not (m in seen or seen.add(m))]

    def _model_chain(self) -> list[str]:
        """返回主力→备用的模型尝试顺序。"""
        chain = [self.primary] + self.fallbacks
        seen = set()
        return [m for m in chain if not (m in seen or seen.add(m))]

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def _call_single(self, model: str, messages: list[dict],
                     temperature: float, max_tokens: int) -> str:
        """调用单个模型。余额不足抛 InsufficientBalanceError 触发切换。"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                resp = client.post(GLM_API_URL, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise BizError(ErrorCode.API_TIMEOUT, f"GLM 调用超时: {model}") from e
        except httpx.HTTPError as e:
            logger.error("GLM 网络错误", model=model, error=str(e))
            raise

        body = resp.json()

        # 余额不足 / 限流 → 切换备用模型
        if resp.status_code == 429 or body.get("error", {}).get("code") in ("1113", "1301"):
            err_msg = body.get("error", {}).get("message", "")
            raise InsufficientBalanceError(f"{model}: {err_msg}")

        if resp.status_code != 200 or "error" in body:
            err_msg = body.get("error", {}).get("message", f"HTTP {resp.status_code}")
            raise BizError(ErrorCode.API_FAILED, f"GLM 调用失败: {err_msg}")

        return body.get("choices", [{}])[0].get("message", {}).get("content", "")

    def chat(self, messages: list[dict], temperature: float = 0.7,
             max_tokens: int = 2000) -> AIResult:
        """统一调用入口：主力失败自动降级到备用模型。"""
        if not self.api_key:
            raise BizError(ErrorCode.API_FAILED, "GLM API Key 未配置")

        start = time.time()
        chain = self._model_chain()

        for i, model in enumerate(chain):
            try:
                content = self._call_single(model, messages, temperature, max_tokens)
                elapsed = int((time.time() - start) * 1000)
                logger.info("AI 调用成功", model=model, elapsed_ms=elapsed, fallback_used=(i > 0))
                return AIResult(
                    content=content, model_used=model,
                    elapsed_ms=elapsed, success=True,
                )
            except InsufficientBalanceError as e:
                logger.warning("模型不可用，切换备用", model=model, error=str(e))
                if i == len(chain) - 1:
                    # 最后一个也失败
                    elapsed = int((time.time() - start) * 1000)
                    return AIResult(
                        content="", model_used=model, elapsed_ms=elapsed,
                        success=False, error=f"所有模型均余额不足: {e}",
                    )
                continue
            except BizError:
                raise
            except Exception as e:
                logger.error("AI 调用异常", model=model, error=str(e))
                if i == len(chain) - 1:
                    raise BizError(ErrorCode.API_FAILED, f"AI 调用失败: {e}")

        # 理论上不会到这里
        raise BizError(ErrorCode.API_FAILED, "AI 调用失败：无可用模型")


# 单例
ai_provider = AIProvider()