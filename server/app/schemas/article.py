"""知识卡 DTO。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArticleCreateIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class PasteIn(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    text: str = Field(min_length=1, max_length=500_000)  # NFR2：单卡正文 ≤ 50 万字符


class ArticlePatchIn(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    summary: str | None = None
    content_md: str | None = Field(default=None, max_length=500_000)


class ArticleRetryIn(BaseModel):
    text: str | None = Field(default=None, max_length=500_000)


class TagOut(BaseModel):
    id: int
    name: str


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    domain: str | None
    title: str | None
    author: str | None
    published_at: dt.datetime | None
    lang: str | None
    word_count: int | None
    summary: str | None
    status: str
    error: str | None
    has_snapshot: bool
    created_at: dt.datetime
    updated_at: dt.datetime


class ArticleDetailOut(ArticleOut):
    content_md: str | None
    content_text: str | None
    tags: list[TagOut] = []
    annotations: list[Any] = []  # M3 填充


class ArticleListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ArticleOut]
