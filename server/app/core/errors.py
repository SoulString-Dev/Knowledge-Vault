"""统一错误体与错误码（架构文档 5.1）：{"code", "message", "details"}。"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status: int = 400

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        if status is not None:
            self.status = status


class C:
    """错误码集中定义，路由层不散落硬编码。"""

    VALIDATION_ERROR = ("VALIDATION_ERROR", 422)
    UNAUTHENTICATED = ("UNAUTHENTICATED", 401)
    TOKEN_INVALID = ("TOKEN_INVALID", 401)
    TOKEN_EXPIRED = ("TOKEN_EXPIRED", 401)
    REFRESH_INVALID = ("REFRESH_INVALID", 401)
    REFRESH_EXPIRED = ("REFRESH_EXPIRED", 401)
    REFRESH_REUSED = ("REFRESH_REUSED", 401)
    INVALID_CREDENTIALS = ("INVALID_CREDENTIALS", 401)
    ACCOUNT_DISABLED = ("ACCOUNT_DISABLED", 403)
    FORBIDDEN = ("FORBIDDEN", 403)
    REGISTER_CLOSED = ("REGISTER_CLOSED", 403)
    INVITE_INVALID = ("INVITE_INVALID", 403)
    NOT_FOUND = ("NOT_FOUND", 404)
    ARTICLE_NOT_FOUND = ("ARTICLE_NOT_FOUND", 404)
    TAG_NOT_FOUND = ("TAG_NOT_FOUND", 404)
    USERNAME_TAKEN = ("USERNAME_TAKEN", 409)
    TAG_EXISTS = ("TAG_EXISTS", 409)
    INVALID_STATE = ("INVALID_STATE", 409)
    RATE_LIMITED = ("RATE_LIMITED", 429)
    INTERNAL = ("INTERNAL", 500)


def err(
    code_pair: tuple[str, int], message: str, *, details: dict[str, Any] | None = None
) -> AppError:
    code, status = code_pair
    return AppError(code, message, status=status, details=details)


class JobTransientError(Exception):
    """任务级可重试错误：runner 会按 attempts 重入队。"""


class JobPermanentError(Exception):
    """任务级不可重试错误：直接标记 failed（分析失败等业务失败也走这里）。"""


class JobGone(Exception):
    """任务目标（article）已不存在：标记 done 跳过（幂等约定）。"""
