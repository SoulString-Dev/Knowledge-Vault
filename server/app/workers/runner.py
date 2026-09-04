"""任务循环：SKIP LOCKED 领取 / 重试 / 僵尸回收 / 清理 / 优雅停机（架构文档 4.3）。"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import time
from pathlib import Path

import structlog
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.core.errors import JobGone, JobPermanentError, JobTransientError
from app.db import get_engine, get_session_factory
from app.logging import setup_logging
from app.models import Article, Job
from app.services import embedder as embedder_mod
from app.workers.handlers import HANDLERS, JobView

log = structlog.get_logger()

CLAIM_SQL = text("""
UPDATE jobs SET status = 'running', locked_at = now()
WHERE id = (
    SELECT id FROM jobs
    WHERE status = 'queued'
    ORDER BY priority, id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING id, type, user_id, article_id, payload, attempts, max_attempts
""")

ZOMBIE_SQL = text(
    "UPDATE jobs SET status = 'queued', locked_at = NULL "
    "WHERE status = 'running' AND locked_at < now() - make_interval(mins => :mins)"
)
# 清理：done 保留 7 天，failed 保留 30 天（v1.2）
CLEANUP_SQL = text(
    "DELETE FROM jobs WHERE (status = 'done' AND finished_at < now() - interval '7 days') "
    "OR (status = 'failed' AND finished_at < now() - interval '30 days')"
)
IDLE_POLL_SECONDS = 1.0
MAINTENANCE_INTERVAL_SECONDS = 60
DAILY_CLEANUP_SECONDS = 86400


async def _process_once(factory: async_sessionmaker[AsyncSession]) -> bool:
    """领取并执行一个任务。返回是否处理了任务。"""
    async with factory() as session:
        row = (await session.execute(CLAIM_SQL)).mappings().first()
        if row is None:
            return False
        job = JobView(row)
        structlog.contextvars.bind_contextvars(job_id=job.id, job_type=job.type)
        handler = HANDLERS.get(job.type)
        try:
            if handler is None:
                raise JobPermanentError(f"未知任务类型：{job.type}")
            await handler(session, job)
            await session.execute(
                update(Job).where(Job.id == job.id).values(status="done", finished_at=func.now())
            )
            await session.commit()
            log.info("job done")
            return True
        except JobGone:
            await session.rollback()
            await _finish_outside(factory, job.id, status="done", error=None)
            log.info("job skipped: article gone")
            return True
        except JobPermanentError as e:
            await session.rollback()
            await _mark_article_failed(factory, job.article_id, str(e))
            await _finish_outside(
                factory, job.id, status="failed", error=str(e)[:2000], failed=True
            )
            log.warning("job failed permanently", error=str(e))
            return True
        except JobTransientError as e:
            await session.rollback()
            await _retry_or_fail(factory, job, e)
            return True
        except Exception as e:  # 未知异常：视为可重试
            await session.rollback()
            log.exception("job crashed")
            await _retry_or_fail(factory, job, e)
            return True
        finally:
            structlog.contextvars.clear_contextvars()


async def _finish_outside(
    factory: async_sessionmaker[AsyncSession],
    job_id: int,
    *,
    status: str,
    error: str | None,
    failed: bool = False,
) -> None:
    values: dict = {"status": status, "locked_at": None, "error": error}
    if failed:
        values["finished_at"] = func.now()
    else:
        values["finished_at"] = func.now()
    async with factory() as session:
        await session.execute(update(Job).where(Job.id == job_id).values(**values))
        await session.commit()


async def _retry_or_fail(
    factory: async_sessionmaker[AsyncSession], job: JobView, exc: Exception
) -> None:
    attempts = job.attempts + 1
    if attempts >= job.max_attempts:
        await _mark_article_failed(factory, job.article_id, str(exc))
        await _finish_outside(factory, job.id, status="failed", error=str(exc)[:2000], failed=True)
        log.warning("job failed after retries", attempts=attempts, error=str(exc))
        return
    async with factory() as session:
        await session.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == "running")
            .values(status="queued", attempts=attempts, locked_at=None)
        )
        await session.commit()
    log.info("job requeued", attempts=attempts, error=str(exc))


async def _mark_article_failed(
    factory: async_sessionmaker[AsyncSession], article_id: int | None, error: str
) -> None:
    if article_id is None:
        return
    async with factory() as session:
        await session.execute(
            update(Article)
            .where(Article.id == article_id, Article.status.in_(["pending", "processing"]))
            .values(status="failed", error=error[:2000])
        )
        await session.commit()


async def _sweep_orphan_snapshots() -> int:
    """清扫快照孤儿文件：磁盘上有、articles.snapshot_path 里没有的。"""
    from app.services.fetcher import delete_snapshot_file

    s = get_settings()
    base = Path(s.app_data_dir)
    snap_dir = base / "snapshots"
    if not snap_dir.is_dir():
        return 0
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.scalars(
                select(Article.snapshot_path).where(Article.snapshot_path.is_not(None))
            )
        ).all()
    valid = set(rows)
    removed = 0
    for f in snap_dir.rglob("*.html.gz"):
        rel = f.relative_to(base).as_posix()
        if rel not in valid:
            delete_snapshot_file(rel)
            removed += 1
    if removed:
        log.info("orphan snapshots removed", count=removed)
    return removed


async def _maintenance_loop(factory: async_sessionmaker[AsyncSession], stop: asyncio.Event) -> None:
    last_daily = 0.0
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=MAINTENANCE_INTERVAL_SECONDS)
            return
        except TimeoutError:
            pass
        try:
            async with factory() as session:
                await session.execute(ZOMBIE_SQL, {"mins": get_settings().job_zombie_minutes})
                await session.commit()
            if time.monotonic() - last_daily >= DAILY_CLEANUP_SECONDS:
                last_daily = time.monotonic()
                async with factory() as session:
                    await session.execute(CLEANUP_SQL)
                    await session.commit()
                await _sweep_orphan_snapshots()
        except Exception:
            log.exception("maintenance error")


async def _worker_loop(factory: async_sessionmaker[AsyncSession], stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            processed = await _process_once(factory)
        except Exception:
            log.exception("worker loop error")
            processed = False
        if not processed:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=IDLE_POLL_SECONDS)


async def run() -> None:
    setup_logging()
    s = get_settings()
    if s.hf_endpoint:
        os.environ.setdefault("HF_ENDPOINT", s.hf_endpoint)
    log.info(
        "worker starting",
        concurrency=s.worker_concurrency,
        embedding_model=s.embedding_model,
    )
    factory = get_session_factory()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _set_stop(*_: object) -> None:
        loop.call_soon_threadsafe(stop.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _set_stop)
        except NotImplementedError:  # Windows ProactorEventLoop
            signal.signal(sig, _set_stop)

    # 模型预热：不阻塞任务领取（首次启动含 ~130MB 模型下载，进度见 HF 日志）
    preload_task = asyncio.create_task(embedder_mod.preload())

    tasks = [asyncio.create_task(_worker_loop(factory, stop)) for _ in range(s.worker_concurrency)]
    maintenance = asyncio.create_task(_maintenance_loop(factory, stop))

    await stop.wait()
    log.info("worker stopping: 等待当前任务完成")
    maintenance.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    preload_task.cancel()
    await get_engine().dispose()
    log.info("worker stopped")


if __name__ == "__main__":
    asyncio.run(run())
