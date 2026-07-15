"""API v1 路由聚合。

Phase 0 仅注册 health；后续 Phase 1 逐步挂载 products/dashboard/config 等路由。
"""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)