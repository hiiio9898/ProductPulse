"""API v1 路由聚合。"""

from fastapi import APIRouter

from app.api.v1 import health, dashboard, products, config, reports

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(products.router)
api_router.include_router(config.router)
api_router.include_router(reports.router)