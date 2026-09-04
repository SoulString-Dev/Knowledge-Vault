"""安全组件测试：bcrypt、JWT、refresh 哈希、限速。"""

import pytest

from app.config import get_settings
from app.core.errors import AppError
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)


def test_password_roundtrip() -> None:
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip() -> None:
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_jwt_garbage_rejected() -> None:
    with pytest.raises(AppError):
        decode_access_token("not-a-jwt")


def test_jwt_expired() -> None:
    s = get_settings()
    original = s.access_token_minutes
    s.access_token_minutes = -1  # 直接改缓存实例：立即过期
    try:
        token = create_access_token(1)
        with pytest.raises(AppError):
            decode_access_token(token)
    finally:
        s.access_token_minutes = original


def test_refresh_token_hash_stable() -> None:
    raw, h = new_refresh_token()
    assert hash_refresh_token(raw) == h
    assert len(h) == 64
    assert raw != h


def test_rate_limit_window() -> None:
    limiter = SlidingWindowLimiter(2)
    limiter.check("ip1")
    limiter.check("ip1")
    with pytest.raises(AppError):
        limiter.check("ip1")
    limiter.check("ip2")  # 不同 key 互不影响
