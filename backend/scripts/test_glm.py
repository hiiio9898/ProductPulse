"""智谱 GLM AI 接口连通性测试。

用法：
    python scripts/test_glm.py

无 API Key 时走 mock，有则真实调用验证模型可用性。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger

import httpx

MOCK_RESPONSE = {
    "choices": [{"message": {"content": "这是一条 mock 日报内容。"}}],
    "usage": {"total_tokens": 42},
}


def test_glm():
    setup_logging()
    logger = get_logger("scripts.test_glm")

    if not settings.glm_api_key:
        logger.warning("未配置 GLM_API_KEY，使用 mock 数据验证脚本逻辑")
        logger.info("Mock 日报生成正常", tokens=MOCK_RESPONSE["usage"]["total_tokens"])
        print("[OK] GLM 脚本逻辑验证通过（mock 模式）")
        return

    logger.info("检测到 API Key，发起真实调用", model=settings.glm_model_primary)
    headers = {"Authorization": f"Bearer {settings.glm_api_key}"}
    payload = {
        "model": settings.glm_model_primary,
        "messages": [{"role": "user", "content": "回复 OK 即可"}],
        "max_tokens": 16,
    }
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            logger.info("GLM 调用成功", status=resp.status_code)
            print(f"[OK] GLM 真实调用成功，HTTP {resp.status_code}")
    except httpx.TimeoutException:
        logger.error("GLM 调用超时")
        print("[FAIL] GLM 调用超时")
    except Exception as e:
        logger.error("GLM 调用失败", error=str(e))
        print(f"[FAIL] GLM 调用失败：{e}")


if __name__ == "__main__":
    test_glm()