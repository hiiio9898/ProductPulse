"""实时汇率服务。

从 exchangerate-api 免费接口获取 USD->CNY 汇率，Redis 缓存 6 小时。
降级：API 不可用时用默认值 7.2。
"""

import json
from typing import Optional

import httpx

from app.core.database import redis_client
from app.core.logging import get_logger

logger = get_logger("services.exchange_rate")

CACHE_KEY = "fx:usd_cny"
CACHE_TTL = 6 * 3600  # 6 小时
DEFAULT_USD_CNY = 7.2


def get_usd_to_cny() -> float:
    """获取 USD->CNY 汇率（缓存 6h，失败用默认值）。"""
    # 先查缓存
    if redis_client:
        try:
            cached = redis_client.get(CACHE_KEY)
            if cached:
                return float(cached)
        except Exception:
            pass

    # 调 API
    rate = _fetch_from_api()
    if rate:
        _save_cache(rate)
        return rate

    logger.warning("汇率 API 失败，用默认值", default=DEFAULT_USD_CNY)
    return DEFAULT_USD_CNY


def _fetch_from_api() -> Optional[float]:
    """从免费汇率 API 获取。"""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get("https://open.er-api.com/v6/latest/USD")
            data = resp.json()
            rate = data.get("rates", {}).get("CNY")
            if rate:
                logger.info("汇率获取成功", usd_cny=rate)
                return round(float(rate), 4)
    except Exception as e:
        logger.warning("汇率 API 调用失败", error=str(e))
    return None


def _save_cache(rate: float) -> None:
    if redis_client:
        try:
            redis_client.setex(CACHE_KEY, CACHE_TTL, str(rate))
        except Exception:
            pass
