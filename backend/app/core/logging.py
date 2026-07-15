"""结构化 JSON 日志 + trace_id 注入。

对应开发规范 7.9：
- 结构化 JSON 格式，含 ts/level/trace_id/module/msg
- 每个 HTTP 请求注入唯一 trace_id，贯穿全链路
- 禁止打印明文 API Key / token / 敏感数据
"""

import logging
import sys
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


def setup_logging() -> None:
    """初始化 structlog，输出结构化 JSON 日志。"""
    level_name = str(settings.log_level).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    return structlog.get_logger(name)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """为每个请求注入唯一 trace_id，写入响应头与日志上下文。"""

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:12]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response