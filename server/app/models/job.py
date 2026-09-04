"""PG 任务表队列（ADR-1）：extract | analyze | embed | annotation_ai | reindex。"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # 部分索引：只索引待领取任务，领取扫描极快
        Index("idx_jobs_claim", "priority", "id", postgresql_where=text("status = 'queued'")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger)  # 无外键：任务独立于业务行生命周期
    article_id: Mapped[int | None] = mapped_column(BigInteger)
    type: Mapped[str] = mapped_column(String(24), nullable=False)
    # queued | running | done | failed
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued", server_default="queued"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="'{}'"
    )
    error: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
