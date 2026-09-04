"""标签管理 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TagRenameIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TagMergeIn(BaseModel):
    src_id: int
    dst_id: int


class TagWithCountOut(BaseModel):
    id: int
    name: str
    article_count: int
