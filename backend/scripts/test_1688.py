"""1688 开放平台 API 连通性测试。

用法：
    python scripts/test_1688.py

无 App Key 时走 mock，有则真实签名调用（需按 1688 SDK 签名，此处为骨架）。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger

import httpx

MOCK_RESPONSE = {
    "code": 0,
    "data": {
        "offer_id": "DEMO_1688_001",
        "title": "PLA 耗材工厂直供 1kg",
        "price": 25.0,
        "currency": "CNY",
    },
}


def test_1688():
    setup_logging()
    logger = get_logger("scripts.test_1688")

    if not settings.ali1688_app_key:
        logger.warning("未配置 ALI1688_APP_KEY，使用 mock 数据验证脚本逻辑")
        logger.info("Mock 响应正常", offer=MOCK_RESPONSE["data"]["offer_id"])
        print("[OK] 1688 脚本逻辑验证通过（mock 模式）")
        return

    logger.info("检测到 App Key，发起真实调用骨架")
    # 注意：1688 需要 HMAC 签名，完整签名逻辑在 Phase 2 的 adapters/ali1688.py 实现
    try:
        with httpx.Client(timeout=10) as client:
            logger.info("1688 真实调用待 Phase 2 实现签名逻辑")
            print("[PENDING] 1688 真实调用需 Phase 2 补充签名逻辑")
    except Exception as e:
        logger.error("1688 调用失败", error=str(e))
        print(f"[FAIL] 1688 调用失败：{e}")


if __name__ == "__main__":
    test_1688()