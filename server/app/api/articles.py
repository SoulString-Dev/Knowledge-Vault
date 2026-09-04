"""知识卡：采集、列表、详情、人工修正、删除、补救、快照回看。"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import C, err
from app.db import get_session
from app.models import Article, ArticleTag, Tag, User
from app.schemas.article import (
    ArticleCreateIn,
    ArticleDetailOut,
    ArticleListOut,
    ArticleOut,
    ArticlePatchIn,
    ArticleRetryIn,
    PasteIn,
    TagOut,
)
from app.services import jobqueue
from app.services.fetcher import (
    delete_snapshot_file,
    host_of,
    md_to_text,
    normalize_url,
    resolve_snapshot_path,
    url_hash,
)

router = APIRouter(prefix="/articles", tags=["articles"])
log = structlog.get_logger()


async def _get_own_article(session: AsyncSession, user_id: int, article_id: int) -> Article:
    article = await session.get(Article, article_id)
    if article is None or article.user_id != user_id:
        raise err(C.ARTICLE_NOT_FOUND, "知识卡不存在")
    return article


async def _tags_of(session: AsyncSession, article_id: int) -> list[TagOut]:
    rows = await session.execute(
        select(Tag.id, Tag.name)
        .join(ArticleTag, ArticleTag.tag_id == Tag.id)
        .where(ArticleTag.article_id == article_id)
        .order_by(Tag.id)
    )
    return [TagOut(id=r.id, name=r.name) for r in rows]


@router.post("", response_model=ArticleOut, status_code=202)
async def create_article(
    body: ArticleCreateIn,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleOut:
    clean = normalize_url(body.url)
    h = url_hash(clean)
    existing = await session.scalar(
        select(Article).where(Article.user_id == user.id, Article.url_hash == h)
    )
    if existing is not None:
        # 重复 URL：返回 200 + 旧卡（FR1.5）
        response.status_code = 200
        return ArticleOut.model_validate(existing)
    article = Article(
        user_id=user.id, url=clean, url_hash=h, domain=host_of(clean), status="pending"
    )
    session.add(article)
    await session.flush()
    await jobqueue.enqueue_job(session, type="extract", user_id=user.id, article_id=article.id)
    await session.commit()
    log.info("article created", article_id=article.id)
    return ArticleOut.model_validate(article)


@router.post("/paste", response_model=ArticleOut, status_code=202)
async def paste_article(
    body: PasteIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleOut:
    text = body.text.strip()
    if not text:
        raise err(C.VALIDATION_ERROR, "粘贴内容不能为空")
    marker = uuid.uuid4().hex
    title = (body.title or text.splitlines()[0] or "粘贴文本").strip()[:512]
    article = Article(
        user_id=user.id,
        url=f"paste://{user.id}/{marker}",
        url_hash=url_hash(f"paste:{user.id}:{marker}"),
        title=title,
        content_md=text,
        content_text=md_to_text(text) or text,
        word_count=len(text),
        status="processing",  # 粘贴跳过抓取，直接进入分析
    )
    session.add(article)
    await session.flush()
    await jobqueue.enqueue_job(session, type="analyze", user_id=user.id, article_id=article.id)
    await session.commit()
    return ArticleOut.model_validate(article)


@router.get("", response_model=ArticleListOut)
async def list_articles(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None, max_length=200),
    tag_id: int | None = None,
    domain: str | None = None,
    status: str | None = None,
    sort: str = Query(default="created", pattern="^(created|updated)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ArticleListOut:
    conds = [Article.user_id == user.id]
    if q:  # 列表内轻量标题过滤；全文检索走 /search
        conds.append(Article.title.ilike(f"%{q}%"))
    if tag_id:
        conds.append(
            Article.id.in_(select(ArticleTag.article_id).where(ArticleTag.tag_id == tag_id))
        )
    if domain:
        conds.append(Article.domain == domain)
    if status:
        conds.append(Article.status == status)
    total = await session.scalar(select(func.count()).select_from(Article).where(*conds)) or 0
    order = Article.created_at.desc() if sort == "created" else Article.updated_at.desc()
    rows = (
        await session.scalars(
            select(Article)
            .where(*conds)
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ArticleListOut(
        total=int(total),
        page=page,
        page_size=page_size,
        items=[ArticleOut.model_validate(a) for a in rows],
    )


@router.get("/{article_id}", response_model=ArticleDetailOut)
async def get_article(
    article_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleDetailOut:
    article = await _get_own_article(session, user.id, article_id)
    return ArticleDetailOut(
        **ArticleOut.model_validate(article).model_dump(),
        content_md=article.content_md,
        content_text=article.content_text,
        tags=await _tags_of(session, article.id),
        annotations=[],  # M3 填充
    )


@router.patch("/{article_id}", response_model=ArticleOut)
async def patch_article(
    article_id: int,
    body: ArticlePatchIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleOut:
    article = await _get_own_article(session, user.id, article_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise err(C.VALIDATION_ERROR, "没有需要修改的字段")
    if "title" in changes:
        article.title = changes["title"]
    if "summary" in changes:
        article.summary = changes["summary"]
    if "content_md" in changes:
        article.content_md = changes["content_md"]
        article.content_text = md_to_text(changes["content_md"])
        article.word_count = len(article.content_text or "")
    # 人工修正 → 重算 tsv + 重嵌入（保持 ADR-3 一致）；失败卡回到处理中
    article.status = "processing" if article.status != "pending" else article.status
    article.error = None
    await jobqueue.enqueue_job(session, type="reindex", user_id=user.id, article_id=article.id)
    await jobqueue.enqueue_job(session, type="embed", user_id=user.id, article_id=article.id)
    await session.commit()
    return ArticleOut.model_validate(article)


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    article = await _get_own_article(session, user.id, article_id)
    snapshot = article.snapshot_path
    await session.delete(article)
    await session.commit()
    # 先提交数据库、再删文件；失败遗留孤儿由 worker 定期清扫
    delete_snapshot_file(snapshot)


@router.post("/{article_id}/reanalyze", response_model=ArticleOut)
async def reanalyze(
    article_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleOut:
    article = await _get_own_article(session, user.id, article_id)
    article.status = "processing"
    article.error = None
    await jobqueue.enqueue_job(session, type="analyze", user_id=user.id, article_id=article.id)
    await session.commit()
    return ArticleOut.model_validate(article)


@router.post("/{article_id}/retry", response_model=ArticleOut)
async def retry_article(
    article_id: int,
    body: ArticleRetryIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArticleOut:
    article = await _get_own_article(session, user.id, article_id)
    if body.text:
        # 手动粘贴文本补救：跳过抓取直接进入分析（FR1.6）
        article.content_md = body.text
        article.content_text = md_to_text(body.text) or body.text
        article.word_count = len(body.text)
        article.status = "processing"
    else:
        if article.status not in {"failed", "pending"}:
            raise err(C.INVALID_STATE, "仅失败或待处理的卡片可重试抓取")
        article.status = "pending"
    article.error = None
    job_type = "analyze" if body.text else "extract"
    await jobqueue.enqueue_job(session, type=job_type, user_id=user.id, article_id=article.id)
    await session.commit()
    return ArticleOut.model_validate(article)


@router.get("/{article_id}/snapshot")
async def get_snapshot(
    article_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    article = await _get_own_article(session, user.id, article_id)
    if not article.snapshot_path:
        raise err(C.NOT_FOUND, "该卡片没有快照")
    path = resolve_snapshot_path(article.snapshot_path)
    if not path.is_file():
        raise err(C.NOT_FOUND, "快照文件不存在")
    # 快照是不可信的第三方 HTML：强制下载 + CSP sandbox，防同源 XSS（4.8）
    return FileResponse(
        path,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="snapshot-{article.id}.html"',
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )
