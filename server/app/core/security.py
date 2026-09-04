"""密码哈希（bcrypt 官方库，passlib 已停更）、JWT 签发校验、refresh token 工具。"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets

import bcrypt
import jwt

from app.config import get_settings
from app.core.errors import C, err

_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(
        "ascii"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + dt.timedelta(minutes=s.access_token_minutes),
    }
    return jwt.encode(payload, s.secret_key.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str) -> int:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key.get_secret_value(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise err(C.TOKEN_EXPIRED, "access token 已过期") from None
    except jwt.InvalidTokenError:
        raise err(C.TOKEN_INVALID, "access token 无效") from None
    if payload.get("type") != "access":
        raise err(C.TOKEN_INVALID, "token 类型错误")
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise err(C.TOKEN_INVALID, "token 主体无效") from None


def new_refresh_token() -> tuple[str, str]:
    """返回 (明文 token, sha256 哈希)。明文只在签发时可见，落库只存哈希（ADR-5）。"""
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
