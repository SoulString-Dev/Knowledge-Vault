"""检索 DTO。"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    tag_id: int | None = None
    domain: str | None = None
    status: str | None = None
    date_from: dt.datetime | None = None
    date_to: dt.datetime | None = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    mode: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SearchHitOut(BaseModel):
    article_id: int
    title: str | None
    url: str
    status: str
    score: float
    snippet: str | None
    tags: list[str] = []
    matched_by: list[str] = []


class SearchOut(BaseModel):
    total: int
    results: list[SearchHitOut]
