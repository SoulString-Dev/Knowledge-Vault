"""批注（M3 使用，表结构随初始迁移建立）。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Annotation(Base):
    __tablename__ = "annotations"
    __table_args__ = (Index("idx_annotations_article", "article_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    article_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # highlight | note | ai
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    quote_text: Mapped[str | None] = mapped_column(Text)  # 选中文本；全文笔记为 NULL
    # {"prefix": "…前30字", "suffix": "…后30字", "occ": 第n次出现}（ADR-4）
    anchor: Mapped[Any] = mapped_column(JSONB, nullable=True)
    note: Mapped[str | None] = mapped_column(Text)  # 手写内容（高亮可为空）
    ai_result: Mapped[str | None] = mapped_column(Text)  # LLM 对选中片段的产出
    color: Mapped[str | None] = mapped_column(String(8), server_default=text("'#ffd54f'"))
    # done | processing | failed（AI 批注用）
    status: Mapped[str] = mapped_column(String(16), server_default=text("'done'"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
