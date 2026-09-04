"""FastAPI 依赖：数据库会话、当前用户、管理员校验。"""

from __future__ import annotations

import structlog
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import C, err
from app.core.security import decode_access_token
from app.db import get_session
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise err(C.UNAUTHENTICATED, "缺少认证信息")
    user_id = decode_access_token(credentials.credentials)
    user = await session.get(User, user_id)
    if user is None:
        raise err(C.UNAUTHENTICATED, "用户不存在")
    if not user.is_active:
        # 禁用后 refresh 即时失效；access 剩余时长（≤30min）内仍可用（4.8 窗口期）
        raise err(C.ACCOUNT_DISABLED, "账号已被禁用")
    structlog.contextvars.bind_contextvars(user_id=user.id)
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise err(C.FORBIDDEN, "需要管理员权限")
    return user
