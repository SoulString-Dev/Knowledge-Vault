"""知识卡：正文、LLM 产物、tsvector 全文索引与向量。"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        UniqueConstraint("user_id", "url_hash", name="uq_articles_user_url_hash"),
        Index("idx_articles_user_created", "user_id", text("created_at DESC")),
        Index("idx_articles_tsv", "search_tsv", postgresql_using="gin"),
        Index(
            "idx_articles_vec",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "idx_articles_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index("idx_articles_domain", "user_id", "domain"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # 规范化 URL 的 sha256（用户内去重，FR1.5）
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    lang: Mapped[str | None] = mapped_column(String(16))
    content_md: Mapped[str | None] = mapped_column(Text)  # 清洗后正文 Markdown
    content_text: Mapped[str | None] = mapped_column(Text)  # 纯文本（检索 / LLM 输入）
    word_count: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)  # LLM 摘要
    # pending → processing → ready / failed
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    error: Mapped[str | None] = mapped_column(Text)
    # app_data 内 .html.gz 相对路径
    snapshot_path: Mapped[str | None] = mapped_column(Text)
    # jieba 分词后写 simple tsvector（worker 维护）
    search_tsv: Mapped[Any] = mapped_column(TSVECTOR, nullable=True)
    # bge-m3 1024 维；换模型需重嵌入（ADR-6）
    embedding: Mapped[Any] = mapped_column(Vector(1024), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    @property
    def has_snapshot(self) -> bool:
        return self.snapshot_path is not None
