"""认证：注册 / 登录 / refresh 轮换与盗用检测（ADR-5）/ 登出 / 当前用户。"""

from __future__ import annotations

import datetime as dt
import re

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.core.errors import C, err
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db import get_session
from app.models import RefreshToken, User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])
log = structlog.get_logger()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_limiter = SlidingWindowLimiter(get_settings().rate_limit_per_min)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _validate_username(username: str) -> None:
    if not USERNAME_RE.fullmatch(username):
        raise err(C.VALIDATION_ERROR, "用户名仅允许 1–32 位字母、数字、_、-（不允许中文）")


async def _issue_tokens(session: AsyncSession, user: User) -> TokenOut:
    s = get_settings()
    raw, token_hash = new_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=_now() + dt.timedelta(days=s.refresh_token_days),
        )
    )
    return TokenOut(
        access_token=create_access_token(user.id),
        refresh_token=raw,
        expires_in=s.access_token_minutes * 60,
    )


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(
    body: RegisterIn, request: Request, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    _limiter.check(f"register:{_client_ip(request)}")
    _validate_username(body.username)
    s = get_settings()
    if s.register_mode == "closed":
        raise err(C.REGISTER_CLOSED, "注册已关闭，请联系管理员建号")
    if s.register_mode == "invite" and (not body.invite_code or body.invite_code != s.invite_code):
        raise err(C.INVITE_INVALID, "邀请码无效")
    if await session.scalar(select(User.id).where(User.username == body.username)):
        raise err(C.USERNAME_TAKEN, "用户名已存在")
    # 首个注册用户自动成为管理员
    is_first = (await session.scalar(select(User.id).limit(1))) is None
    user = User(
        username=body.username, password_hash=hash_password(body.password), is_admin=is_first
    )
    session.add(user)
    await session.flush()
    tokens = await _issue_tokens(session, user)
    await session.commit()
    log.info("user registered", username=body.username, is_admin=is_first)
    return tokens


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn, request: Request, session: AsyncSession = Depends(get_session)
) -> TokenOut:
    _limiter.check(f"login:{_client_ip(request)}")
    user = await session.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise err(C.INVALID_CREDENTIALS, "用户名或密码错误")
    if not user.is_active:
        raise err(C.ACCOUNT_DISABLED, "账号已被禁用")
    tokens = await _issue_tokens(session, user)
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, session: AsyncSession = Depends(get_session)) -> TokenOut:
    token_hash = hash_refresh_token(body.refresh_token)
    row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is None:
        raise err(C.REFRESH_INVALID, "refresh token 无效")
    if row.revoked:
        # 复用检测：已吊销的 token 再次使用 → 吊销该用户全部 refresh（ADR-5）
        await session.execute(
            update(RefreshToken).where(RefreshToken.user_id == row.user_id).values(revoked=True)
        )
        await session.commit()
        log.warning("refresh token reuse detected", user_id=row.user_id)
        raise err(C.REFRESH_REUSED, "refresh token 已失效，为保护账号已吊销全部会话，请重新登录")
    if row.expires_at <= _now():
        raise err(C.REFRESH_EXPIRED, "refresh token 已过期")
    # 原子认领：并发轮换时只有一个请求能成功
    claimed = (
        (
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.id == row.id, RefreshToken.revoked.is_(False))
                .values(revoked=True)
                .returning(RefreshToken.id)
            )
        )
        .scalars()
        .first()
    )
    if claimed is None:
        raise err(C.REFRESH_REUSED, "refresh token 已被使用，请重新登录")
    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise err(C.UNAUTHENTICATED, "用户不可用")
    tokens = await _issue_tokens(session, user)
    await session.commit()
    return tokens


@router.post("/logout", status_code=204)
async def logout(body: RefreshIn, session: AsyncSession = Depends(get_session)) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(body.refresh_token))
        .values(revoked=True)
    )
    await session.commit()


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)
