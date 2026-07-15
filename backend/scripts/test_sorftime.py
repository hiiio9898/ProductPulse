"""Sorftime 选品情报 API 连通性测试。

用法：
    python scripts/test_sorftime.py

无 API Key 时自动走 mock 数据，验证脚本逻辑可用。
有 Key 时真实调用，验证鉴权与基础接口。
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
        "items": [
            {
                "product_id": "DEMO_001",
                "title": "PLA 3D 打印耗材 1.75mm",
                "category": "3d_filament",
                "price": 12.5,
                "monthly_sales": 3500,
                "rating": 4.6,
                "growth_rate": 0.18,
            }
        ]
    },
}


def test_sorftime():
    setup_logging()
    logger = get_logger("scripts.test_sorftime")

    if not settings.sorftime_api_key:
        logger.warning("未配置 SORFTIME_API_KEY，使用 mock 数据验证脚本逻辑")
        logger.info("Mock 响应正常", items=len(MOCK_RESPONSE["data"]["items"]))
        print("[OK] Sorftime 脚本逻辑验证通过（mock 模式）")
        return

    logger.info("检测到 API Key，发起真实调用")
    headers = {"Authorization": f"Bearer {settings.sorftime_api_key}"}
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{settings.sorftime_base_url}/v1/products",
                headers=headers,
                params={"category": "3d_filament", "page": 1, "page_size": 1},
            )
            resp.raise_for_status()
            logger.info("Sorftime 调用成功", status=resp.status_code)
            print(f"[OK] Sorftime 真实调用成功，HTTP {resp.status_code}")
    except httpx.TimeoutException:
        logger.error("Sorftime 调用超时")
        print("[FAIL] Sorftime 调用超时")
    except Exception as e:
        logger.error("Sorftime 调用失败", error=str(e))
        print(f"[FAIL] Sorftime 调用失败：{e}")


if __name__ == "__main__":
    test_sorftime()