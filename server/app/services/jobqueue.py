"""任务入队辅助（PG 任务表队列，ADR-1）。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job


async def enqueue_job(
    session: AsyncSession,
    *,
    type: str,
    user_id: int | None,
    article_id: int | None,
    priority: int = 5,
    payload: dict | None = None,
) -> Job:
    job = Job(
        user_id=user_id,
        article_id=article_id,
        type=type,
        priority=priority,
        payload=payload or {},
    )
    session.add(job)
    await session.flush()
    return job


async def has_active_job(session: AsyncSession, article_id: int, type: str) -> bool:
    """幂等保护：同卡同类型任务已在排队 / 执行中则不再重复入队。"""
    from sqlalchemy import select

    stmt = (
        select(Job.id)
        .where(
            Job.article_id == article_id,
            Job.type == type,
            Job.status.in_(["queued", "running"]),
        )
        .limit(1)
    )
    return (await session.scalar(stmt)) is not None
