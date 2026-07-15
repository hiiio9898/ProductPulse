"""健康检查路由。

无鉴权，供监控探活使用。对应 5.2.4 GET /api/v1/health。
"""

from fastapi import APIRouter

from app.core.response import ok_response

router = APIRouter()


@router.get("/health", tags=["system"])
async def health():
    """健康检查。"""
    return ok_response(data={"status": "ok"})