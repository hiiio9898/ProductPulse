"""统一响应体与业务异常。

对应 API 文档 5.1 的统一响应格式：
    {"code": 0, "message": "success", "data": {}, "timestamp": "..."}
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ---------- 错误码（与 5.1 错误码定义一致）----------
class ErrorCode:
    SUCCESS = 0
    PARAM_INVALID = 1001
    NOT_FOUND = 1002
    API_TIMEOUT = 2001
    API_FAILED = 2002
    DB_ERROR = 3001
    NO_PERMISSION = 4001
    RATE_LIMIT = 429
    INTERNAL = 5001


def now_iso() -> str:
    """ISO 8601 UTC 时间戳。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ApiResponse(BaseModel):
    """统一响应结构。"""

    code: int = ErrorCode.SUCCESS
    message: str = "success"
    data: Optional[Any] = None
    timestamp: str = ""

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> "ApiResponse":
        return cls(code=ErrorCode.SUCCESS, message=message, data=data, timestamp=now_iso())

    @classmethod
    def fail(cls, code: int, message: str, data: Any = None) -> "ApiResponse":
        return cls(code=code, message=message, data=data, timestamp=now_iso())


def ok_response(data: Any = None, message: str = "success") -> JSONResponse:
    """快捷构造成功响应。"""
    payload = ApiResponse.ok(data=data, message=message)
    return JSONResponse(content=jsonable_encoder(payload), status_code=200)


# ---------- 业务异常 ----------
class BizError(Exception):
    """业务异常，被全局 handler 捕获后转为统一响应体。"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def register_exception_handlers(app):
    """注册全局异常处理器。"""

    @app.exception_handler(BizError)
    async def _biz_handler(_: Request, e: BizError):
        payload = ApiResponse.fail(code=e.code, message=e.message, data=e.data)
        return JSONResponse(content=jsonable_encoder(payload), status_code=200)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, e: RequestValidationError):
        payload = ApiResponse.fail(
            code=ErrorCode.PARAM_INVALID,
            message="参数校验失败",
            data=jsonable_encoder(e.errors()),
        )
        return JSONResponse(content=jsonable_encoder(payload), status_code=200)

    @app.exception_handler(Exception)
    async def _global_handler(_: Request, e: Exception):
        payload = ApiResponse.fail(
            code=ErrorCode.INTERNAL, message="系统内部错误", data=None
        )
        # 完整栈交给日志，不暴露给客户端
        return JSONResponse(content=jsonable_encoder(payload), status_code=500)