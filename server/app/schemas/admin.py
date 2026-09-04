"""管理员 DTO。"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class AdminUserCreateIn(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    is_admin: bool = False


class AdminUserPatchIn(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_admin: bool
    is_active: bool
    created_at: dt.datetime


class AdminUserListOut(BaseModel):
    total: int
    items: list[AdminUserOut]


class JobOut(BaseModel):
    id: int
    type: str
    status: str
    attempts: int
    max_attempts: int
    article_id: int | None
    error: str | None
    created_at: dt.datetime
    finished_at: dt.datetime | None


class AdminJobsOut(BaseModel):
    stats: dict[str, int]
    failed: list[JobOut]
