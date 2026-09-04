"""服务端管理命令：python -m app.cli <command>

reembed：换 embedding 模型 / 维度后全量重入队 embed 任务（架构文档 4.2 / ADR-6）。
用法：
    python -m app.cli reembed            # 仅为有正文但缺向量的卡片入队
    python -m app.cli reembed --force    # 已有向量的卡片也重新入队（换模型后必须）
"""

from __future__ import annotations

import argparse
import asyncio

import structlog
from sqlalchemy import func, select

from app.config import get_settings
from app.db import dispose_engine, get_session_factory
from app.logging import setup_logging
from app.models import Article
from app.services.jobqueue import enqueue_job

log = structlog.get_logger()


async def _reembed(force: bool) -> int:
    s = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        conds = [Article.content_text.is_not(None)]
        if not force:
            conds.append(Article.embedding.is_(None))
        total = (
            await session.scalar(select(func.count()).select_from(Article).where(*conds)) or 0
        )
        log.info(
            "reembed: enqueueing",
            total=int(total),
            model=s.embedding_model,
            dim=s.embedding_dim,
            force=force,
        )
        ids = (
            await session.scalars(
                select(Article.id).where(*conds).order_by(Article.id).limit(10000)
            )
        ).all()
        for article_id in ids:
            # 批量重嵌入优先级放低（7 > 5），不与用户新卡片任务抢队列
            await enqueue_job(
                session, type="embed", user_id=None, article_id=int(article_id), priority=7
            )
        await session.commit()
        return int(total)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(prog="app.cli", description="知识匣服务端管理命令")
    sub = parser.add_subparsers(dest="command", required=True)
    p_reembed = sub.add_parser("reembed", help="全量重嵌入（换 embedding 模型后执行）")
    p_reembed.add_argument(
        "--force", action="store_true", help="已有向量的卡片也重新入队（换模型 / 维度后必须）"
    )
    args = parser.parse_args()

    if args.command == "reembed":
        count = asyncio.run(_reembed(args.force))
        print(f"已入队 {count} 个 embed 任务，由 worker 执行。")
    asyncio.run(dispose_engine())


if __name__ == "__main__":
    main()
