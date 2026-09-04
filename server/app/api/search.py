"""检索路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_session
from app.models import User
from app.schemas.search import SearchHitOut, SearchIn, SearchOut
from app.services.search import (
    _attach_tags,
    _trigram_fallback,
    hybrid_search,
    keyword_search,
    semantic_search,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchOut)
async def search(
    body: SearchIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SearchOut:
    if body.mode == "keyword":
        hits = await keyword_search(session, user.id, body.query, body.filters)
        if not hits:  # 单 token 或无命中时 trigram 兜底
            hits = await _trigram_fallback(session, user.id, body.query, body.filters)
        total = len(hits)
    elif body.mode == "semantic":
        hits = await semantic_search(session, user.id, body.query, body.filters)
        total = len(hits)
    else:
        hits, total = await hybrid_search(session, user.id, body.query, body.filters)
    await _attach_tags(session, hits)
    return SearchOut(
        total=total,
        results=[
            SearchHitOut(
                article_id=h.article_id,
                title=h.title,
                url=h.url,
                status=h.status,
                score=h.score,
                snippet=h.snippet,
                tags=h.tags,
                matched_by=h.matched_by,
            )
            for h in hits
        ],
    )
