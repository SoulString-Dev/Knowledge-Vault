"""检索引擎（架构文档 4.7）：keyword / semantic / hybrid（RRF 融合）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, ArticleTag, Tag
from app.schemas.search import SearchFilters
from app.services import embedder
from app.services.tokenizer_cn import build_tsquery_or

RRF_K = 60
CANDIDATES = 20  # 两路各取 top-20 再融合
SNIPPET_MAX = 300
_SEMANTIC_LEAD_CHARS = 160

_HEADLINE_OPTS = "StartSel=<em>, StopSel=</em>, MaxFragments=2, MaxWords=40, MinWords=15"


@dataclass
class SearchHit:
    article_id: int
    title: str | None
    url: str
    status: str
    score: float
    snippet: str | None
    matched_by: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _where(user_id: int, f: SearchFilters) -> list:
    """过滤器共同下推（tag / domain / 时间范围 / status）。"""
    conds: list = [Article.user_id == user_id]
    if f.status:
        conds.append(Article.status == f.status)
    if f.domain:
        conds.append(Article.domain == f.domain)
    if f.tag_id:
        conds.append(
            Article.id.in_(select(ArticleTag.article_id).where(ArticleTag.tag_id == f.tag_id))
        )
    if f.date_from:
        conds.append(Article.created_at >= f.date_from)
    if f.date_to:
        conds.append(Article.created_at <= f.date_to)
    return conds


async def _attach_tags(session: AsyncSession, hits: list[SearchHit]) -> None:
    ids = [h.article_id for h in hits]
    if not ids:
        return
    rows = await session.execute(
        select(ArticleTag.article_id, Tag.name)
        .join(Tag, Tag.id == ArticleTag.tag_id)
        .where(ArticleTag.article_id.in_(ids))
    )
    by_article: dict[int, list[str]] = {}
    for article_id, name in rows:
        by_article.setdefault(article_id, []).append(name)
    for h in hits:
        h.tags = by_article.get(h.article_id, [])


async def keyword_search(
    session: AsyncSession, user_id: int, query: str, f: SearchFilters, limit: int = CANDIDATES
) -> list[SearchHit]:
    tsq = build_tsquery_or(query)
    if not tsq:
        return []
    tq = func.to_tsquery("simple", tsq)
    rank = func.ts_rank_cd(Article.search_tsv, tq)
    headline = func.ts_headline("simple", Article.content_text, tq, _HEADLINE_OPTS)
    # hnsw.ef_search 默认即为 40，无需显式设置
    stmt = (
        select(Article.id, Article.title, Article.url, Article.status, rank, headline)
        .where(Article.search_tsv.op("@@")(tq), *_where(user_id, f))
        .order_by(rank.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        SearchHit(
            article_id=r.id,
            title=r.title,
            url=r.url,
            status=r.status,
            score=float(r.rank or 0.0),
            snippet=(r.headline or "")[:SNIPPET_MAX],
            matched_by=["keyword"],
        )
        for r in rows
    ]


async def _trigram_fallback(
    session: AsyncSession, user_id: int, query: str, f: SearchFilters, limit: int = CANDIDATES
) -> list[SearchHit]:
    """单 token 或无命中时按标题模糊匹配兜底（pg_trgm）。"""
    stmt = (
        select(
            Article.id,
            Article.title,
            Article.url,
            Article.status,
            func.similarity(Article.title, query).label("sim"),
        )
        .where(Article.title.is_not(None), Article.title.ilike(f"%{query}%"), *_where(user_id, f))
        .order_by(func.similarity(Article.title, query).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        SearchHit(
            article_id=r.id,
            title=r.title,
            url=r.url,
            status=r.status,
            score=float(r.sim or 0.0),
            snippet=None,
            matched_by=["keyword"],
        )
        for r in rows
    ]


async def semantic_search(
    session: AsyncSession, user_id: int, query: str, f: SearchFilters, limit: int = CANDIDATES
) -> list[SearchHit]:
    vec = (await embedder.encode_batch([query]))[0]
    dist = Article.embedding.cosine_distance(vec)
    stmt = (
        select(
            Article.id,
            Article.title,
            Article.url,
            Article.status,
            dist.label("dist"),
            func.left(Article.content_text, _SEMANTIC_LEAD_CHARS).label("lead"),
        )
        .where(Article.embedding.is_not(None), *_where(user_id, f))
        .order_by(dist.asc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        SearchHit(
            article_id=r.id,
            title=r.title,
            url=r.url,
            status=r.status,
            score=round(1.0 - float(r.dist), 6),
            snippet=(r.lead or "")[:SNIPPET_MAX],
            matched_by=["semantic"],
        )
        for r in rows
    ]


def rrf_merge(kw: list[SearchHit], se: list[SearchHit]) -> list[SearchHit]:
    """RRF 融合：score = Σ 1/(k + rank)。纯函数便于单测。"""
    scores: dict[int, float] = {}
    matched: dict[int, set[str]] = {}
    hits: dict[int, SearchHit] = {}
    for ranked in (kw, se):
        for rank, hit in enumerate(ranked, start=1):
            scores[hit.article_id] = scores.get(hit.article_id, 0.0) + 1.0 / (RRF_K + rank)
            matched.setdefault(hit.article_id, set()).update(hit.matched_by)
            hits.setdefault(hit.article_id, hit)
    merged: list[SearchHit] = []
    for article_id, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
        hit = hits[article_id]
        hit.score = score
        hit.matched_by = sorted(matched[article_id])
        merged.append(hit)
    return merged


async def hybrid_search(
    session: AsyncSession, user_id: int, query: str, f: SearchFilters
) -> tuple[list[SearchHit], int]:
    kw = await keyword_search(session, user_id, query, f)
    if not kw:
        kw = await _trigram_fallback(session, user_id, query, f)
    se = await semantic_search(session, user_id, query, f)
    merged = rrf_merge(kw, se)
    return merged, len(merged)
