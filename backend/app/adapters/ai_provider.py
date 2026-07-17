"""AI 大模型适配层（FR-03）。

统一封装智谱 GLM 调用，支持：
- 主力模型自动降级到备用模型（GLM-5.2 -> GLM-4.7 -> glm-4-flash）
- 429 限流自动重试（指数退避，最多 6 次），重试进度写入 Redis 供前端查询
- 余额不足(1113)/无资源包(1301) 时切换备用模型
- 统一返回结构 + 耗时统计
"""

import time
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.response import BizError, ErrorCode

logger = get_logger("adapters.ai_provider")

GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_TIMEOUT = 60
MAX_RATE_LIMIT_RETRIES = 6


@dataclass
class AIResult:
    """大模型调用结果。"""

    content: str
    model_used: str
    elapsed_ms: int
    success: bool
    error: Optional[str] = None
    retries: int = 0


class InsufficientBalanceError(Exception):
    """余额不足或无资源包，应切换备用模型。"""


class RateLimitError(Exception):
    """429 限流，应等待后重试当前模型。"""

    def __init__(self, model: str, message: str = ""):
        self.model = model
        self.message = message
        super().__init__(f"{model}: {message}")


def _report_retry_progress(task_id, model: str, attempt: int, max_retries: int):
    """将重试进度写入 Redis，供前端轮询。"""
    if not task_id:
        return
    try:
        from app.core.database import redis_client
        if redis_client:
            import json
            progress = {
                "status": "retrying",
                "model": model,
                "attempt": attempt,
                "max_retries": max_retries,
                "message": f"Model {model} rate limited, retrying ({attempt}/{max_retries})...",
            }
            redis_client.setex(f"ai:report:{task_id}", 300, json.dumps(progress))
    except Exception:
        pass


class AIProvider:
    """智谱 GLM 统一适配层。"""

    def __init__(self, api_key=None, primary=None, fallbacks=None):
        self.api_key = api_key or settings.glm_api_key
        self.primary = primary or settings.glm_model_primary
        self.fallbacks = fallbacks or self._load_fallbacks()

    @staticmethod
    def _load_fallbacks():
        defaults = ["glm-4.7", "glm-4-flash"]
        configured = settings.glm_model_fallback
        if configured and configured != settings.glm_model_primary:
            defaults.insert(0, configured)
        chain = [settings.glm_model_primary] + defaults
        seen = set()
        return [m for m in chain if not (m in seen or seen.add(m))]

    def _model_chain(self):
        chain = [self.primary] + self.fallbacks
        seen = set()
        return [m for m in chain if not (m in seen or seen.add(m))]

    def _call_single(self, model, messages, temperature, max_tokens, task_id=None):
        """调用单个模型。429 重试，1113 降级。"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            try:
                with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
                    resp = client.post(GLM_API_URL, headers=headers, json=payload)
            except httpx.TimeoutException as e:
                raise BizError(ErrorCode.API_TIMEOUT, f"GLM timeout: {model}") from e
            except httpx.HTTPError as e:
                logger.error("GLM network error", model=model, error=str(e))
                raise

            body = {}
            try:
                body = resp.json()
            except Exception:
                pass

            err_code = str(body.get("error", {}).get("code", "")) if isinstance(body, dict) else ""
            err_msg = body.get("error", {}).get("message", "") if isinstance(body, dict) else ""

            # 429 限流 -> 重试
            if resp.status_code == 429:
                if attempt < MAX_RATE_LIMIT_RETRIES:
                    wait_sec = min(2 ** attempt, 8)
                    logger.warning("GLM rate limited, retrying",
                                   model=model, attempt=attempt,
                                   max_retries=MAX_RATE_LIMIT_RETRIES, wait=wait_sec)
                    _report_retry_progress(task_id, model, attempt, MAX_RATE_LIMIT_RETRIES)
                    time.sleep(wait_sec)
                    continue
                raise RateLimitError(model, f"Retried {MAX_RATE_LIMIT_RETRIES} times")

            # 余额不足 -> 降级
            if err_code in ("1113", "1301"):
                raise InsufficientBalanceError(f"{model}: {err_msg}")

            if resp.status_code != 200 or (isinstance(body, dict) and "error" in body):
                raise BizError(ErrorCode.API_FAILED, f"GLM failed: {err_msg or resp.status_code}")

            return body.get("choices", [{}])[0].get("message", {}).get("content", "")

        raise RateLimitError(model, "Max retries exhausted")

    def chat(self, messages, temperature=0.7, max_tokens=2000, task_id=None):
        """统一调用入口。429 重试同一模型，余额不足降级。"""
        if not self.api_key:
            raise BizError(ErrorCode.API_FAILED, "GLM API Key not configured")

        start = time.time()
        chain = self._model_chain()
        total_retries = 0

        for i, model in enumerate(chain):
            try:
                content = self._call_single(model, messages, temperature, max_tokens, task_id=task_id)
                elapsed = int((time.time() - start) * 1000)
                logger.info("AI success", model=model, elapsed_ms=elapsed, fallback_used=(i > 0))
                return AIResult(content=content, model_used=model,
                                elapsed_ms=elapsed, success=True, retries=total_retries)
            except InsufficientBalanceError as e:
                logger.warning("Model insufficient balance, switching", model=model, error=str(e))
                if i == len(chain) - 1:
                    elapsed = int((time.time() - start) * 1000)
                    return AIResult(content="", model_used=model, elapsed_ms=elapsed,
                                    success=False, error=f"All models insufficient balance: {e}")
                continue
            except RateLimitError as e:
                logger.warning("Model rate limited after retries, switching", model=model, error=str(e))
                total_retries += MAX_RATE_LIMIT_RETRIES
                if i == len(chain) - 1:
                    elapsed = int((time.time() - start) * 1000)
                    return AIResult(content="", model_used=model, elapsed_ms=elapsed,
                                    success=False, error=f"All models rate limited: {e}")
                continue
            except BizError:
                raise
            except Exception as e:
                logger.error("AI error", model=model, error=str(e))
                if i == len(chain) - 1:
                    raise BizError(ErrorCode.API_FAILED, f"AI failed: {e}")

        raise BizError(ErrorCode.API_FAILED, "AI failed: no available model")


ai_provider = AIProvider()
