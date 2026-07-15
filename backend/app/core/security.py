"""鉴权依赖。

单用户系统：通过请求头 Authorization: Bearer <token> 校验。
token 为 .env 中配置的 APP_SECRET_KEY（生产应替换为独立访问令牌）。
"""

import secrets

from fastapi import Depends, Header, Request

from app.core.config import settings
from app.core.response import BizError, ErrorCode


async def verify_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> bool:
    """校验 Bearer Token。

    健康检查等公开接口不走此依赖；其余 API 必须携带有效 token。
    """
    # 健康检查路径放行
    if request.url.path.endswith("/health"):
        return True

    if not authorization or not authorization.startswith("Bearer "):
        raise BizError(code=ErrorCode.NO_PERMISSION, message="缺少鉴权信息")

    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, settings.app_secret_key):
        raise BizError(code=ErrorCode.NO_PERMISSION, message="鉴权失败")

    return True


# 便捷导出
AuthRequired = Depends(verify_token)