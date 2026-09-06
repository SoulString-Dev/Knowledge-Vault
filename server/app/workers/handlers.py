"""任务处理器：extract / analyze / embed / reindex（annotation_ai 属 M3）。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AntiBotBlockedError,
    JobGone,
    JobPermanentError,
)
from app.models import Article, ArticleTag, Tag
from app.services import embedder as embedder_mod
from app.services import llm
from app.services.embedder import build_embed_input
from app.services.fetcher import (
    QualityGateError,
    extract_content,
    fetch_html,
    host_of,
    md_to_text,
    parse_published_at,
    render_with_cdp,
    save_render_debug,
    save_snapshot,
)
from app.services.jobqueue import enqueue_job, has_active_job
from app.services.llm import tag_key
from app.services.tokenizer_cn import build_tsvector_input

log = structlog.get_logger()

Handler = Callable[[AsyncSession, "JobView"], Awaitable[None]]


class JobView:
    """jobs 行的轻量视图（来自 SKIP LOCKED 领取查询）。"""

    def __init__(self, row: Any) -> None:
        self.id: int = row["id"]
        self.type: str = row["type"]
        self.user_id: int | None = row["user_id"]
        self.article_id: int | None = row["article_id"]
        self.payload: dict = row["payload"] or {}
        self.attempts: int = row["attempts"]
        self.max_attempts: int = row["max_attempts"]


async def _get_article(session: AsyncSession, article_id: int | None) -> Article:
    if article_id is None:
        raise JobGone()
    article = await session.get(Article, article_id)
    if article is None:
        raise JobGone()  # 文章已删除：任务标记 done 跳过（幂等约定）
    return article


async def _render_fallback(url: str) -> str:
    from app.config import get_settings

    s = get_settings()
    if not s.playwright_cdp_url:
        raise JobPermanentError("正文抽取质量不足，且未配置 JS 渲染兜底（PLAYWRIGHT_CDP_URL）")
    return await render_with_cdp(url)


async def handle_extract(session: AsyncSession, job: JobView) -> None:
    from app.config import get_settings

    s = get_settings()
    article = await _get_article(session, job.article_id)
    if article.content_md:
        # 幂等：已抽取过（重试安全），确保后续任务在队即可
        if not await has_active_job(session, article.id, "analyze"):
            await enqueue_job(
                session, type="analyze", user_id=article.user_id, article_id=article.id
            )
        return

    # 三种情况转渲染兜底（4.4：质量不足、抽取失败、抓取被反爬拦截）：
    content = None
    html: str | None = None
    final_url = article.url
    try:
        html, final_url = await fetch_html(article.url)
    except AntiBotBlockedError:
        if not s.playwright_cdp_url:
            raise  # 未配置兜底：保持 403 原始指引信息
    else:
        try:
            content = extract_content(html, final_url)
        except QualityGateError:
            content = None  # 抽到了但太短 → 渲染重抽
        except JobPermanentError:
            if not s.playwright_cdp_url:
                raise  # 抽取失败（如拿到 JS 壳子）且无兜底
            content = None

    if content is None:
        html = await _render_fallback(article.url)
        try:
            content = extract_content(html, final_url)
        except (QualityGateError, JobPermanentError) as e:
            # 渲染兜底后仍抽取不到：落盘渲染 HTML 供排查，错误里带规模与产物路径
            debug_path = save_render_debug(article.id, html)
            suffix = f"；渲染 HTML 已存 {debug_path}" if debug_path else ""
            raise JobPermanentError(
                f"渲染兜底后仍未抽取到正文（渲染 HTML {len(html)} 字符，"
                f"最终 URL: {final_url}{suffix}）"
            ) from e

    assert html is not None  # content 非 None 时 html 必然已在 fetch 或 render 中取得
    article.title = content.get("title") or article.title
    article.author = content.get("author")
    article.published_at = parse_published_at(content.get("date"))
    article.lang = content.get("language")
    article.domain = host_of(final_url) or article.domain
    article.content_md = str(content["text"])
    article.content_text = md_to_text(str(content["text"]))
    article.word_count = len(article.content_text or "")
    article.snapshot_path = save_snapshot(article.user_id, article.id, html)
    article.status = "processing"
    article.error = None
    await enqueue_job(session, type="analyze", user_id=article.user_id, article_id=article.id)


async def handle_analyze(session: AsyncSession, job: JobView) -> None:
    article = await _get_article(session, job.article_id)
    if article.summary is not None:
        # 幂等：已分析过（重试安全）
        if not await has_active_job(session, article.id, "embed"):
            await enqueue_job(session, type="embed", user_id=article.user_id, article_id=article.id)
        return
    if not article.content_text:
        raise JobPermanentError("正文为空，无法分析：该卡片尚未成功抓取正文，请先「重试」抓取")
    summary, tags = await llm.summarize_and_tags(article.title or article.url, article.content_text)
    article.summary = summary
    # 打标：优先沿用用户已有标签的措辞（FR2.2）
    existing = {
        tag_key(t.name): t
        for t in (await session.scalars(select(Tag).where(Tag.user_id == article.user_id))).all()
    }
    for name in tags:
        key = tag_key(name)
        tag = existing.get(key)
        if tag is None:
            tag = Tag(user_id=article.user_id, name=name)
            session.add(tag)
            await session.flush()
            existing[key] = tag
        linked = await session.scalar(
            select(ArticleTag.article_id).where(
                ArticleTag.article_id == article.id, ArticleTag.tag_id == tag.id
            )
        )
        if linked is None:
            session.add(ArticleTag(article_id=article.id, tag_id=tag.id))
    await enqueue_job(session, type="embed", user_id=article.user_id, article_id=article.id)


async def _apply_tsv(session: AsyncSession, article: Article) -> None:
    tsv_input = build_tsvector_input(article.title, article.summary, article.content_text)
    article.search_tsv = func.to_tsvector("simple", tsv_input) if tsv_input else None


async def handle_embed(session: AsyncSession, job: JobView) -> None:
    article = await _get_article(session, job.article_id)
    if article.status == "ready" and article.embedding is not None:
        return  # 幂等：重试安全
    if not article.content_text:
        raise JobPermanentError("正文为空，无法向量化")
    vec = (
        await embedder_mod.encode_batch(
            [build_embed_input(article.title, article.summary, article.content_text)]
        )
    )[0]
    await _apply_tsv(session, article)
    article.embedding = vec
    article.status = "ready"
    article.error = None


async def handle_reindex(session: AsyncSession, job: JobView) -> None:
    """仅重算 search_tsv，不重嵌入（PATCH 人工修正用）。"""
    article = await _get_article(session, job.article_id)
    await _apply_tsv(session, article)


async def handle_annotation_ai(session: AsyncSession, job: JobView) -> None:  # pragma: no cover
    raise JobPermanentError("AI 批注属于 M3 里程碑，M1 未实现")


HANDLERS: dict[str, Handler] = {
    "extract": handle_extract,
    "analyze": handle_analyze,
    "embed": handle_embed,
    "reindex": handle_reindex,
    "annotation_ai": handle_annotation_ai,
}
