"""FastAPI 应用入口。

启动：uvicorn app.main:app --reload
文档：/docs (Swagger) / /redoc
"""

from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import TraceIdMiddleware, get_logger, setup_logging
from app.core.response import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化日志，检查依赖连接。"""
    setup_logging()
    logger = get_logger("app.main")
    logger.info("应用启动", env=settings.app_env, port=settings.app_port)

    # Redis 连通性检查（非阻塞，失败仅告警）
    try:
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        logger.info("Redis 连接正常")
    except Exception as e:
        logger.warning("Redis 连接失败，定时任务暂不可用", error=str(e))

    yield
    logger.info("应用关闭")


def create_app() -> FastAPI:
    """应用工厂。"""
    app = FastAPI(
        title="ProductPulse API",
        description="外贸选品决策系统 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # trace_id 注入
    app.add_middleware(TraceIdMiddleware)

    # 异常处理
    register_exception_handlers(app)

    # 路由
    app.include_router(api_router)

    return app


app = create_app()