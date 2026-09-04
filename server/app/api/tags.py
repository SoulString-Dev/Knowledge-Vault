"""标签管理：列表（含计数）、重命名、删除、合并（FR2.6 / F6）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import C, err
from app.db import get_session
from app.models import ArticleTag, Tag, User
from app.schemas.tag import TagMergeIn, TagRenameIn, TagWithCountOut

router = APIRouter(prefix="/tags", tags=["tags"])


async def _get_own_tag(session: AsyncSession, user_id: int, tag_id: int) -> Tag:
    tag = await session.get(Tag, tag_id)
    if tag is None or tag.user_id != user_id:
        raise err(C.TAG_NOT_FOUND, "标签不存在")
    return tag


@router.get("", response_model=list[TagWithCountOut])
async def list_tags(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TagWithCountOut]:
    rows = await session.execute(
        select(Tag.id, Tag.name, func.count(ArticleTag.article_id))
        .outerjoin(ArticleTag, ArticleTag.tag_id == Tag.id)
        .where(Tag.user_id == user.id)
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(ArticleTag.article_id).desc(), Tag.name)
    )
    return [TagWithCountOut(id=r[0], name=r[1], article_count=int(r[2])) for r in rows]


@router.patch("/{tag_id}", response_model=TagWithCountOut)
async def rename_tag(
    tag_id: int,
    body: TagRenameIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TagWithCountOut:
    tag = await _get_own_tag(session, user.id, tag_id)
    exists = await session.scalar(
        select(Tag.id).where(Tag.user_id == user.id, Tag.name == body.name, Tag.id != tag_id)
    )
    if exists:
        raise err(C.TAG_EXISTS, "同名标签已存在")
    tag.name = body.name
    await session.commit()
    count = await session.scalar(
        select(func.count()).select_from(ArticleTag).where(ArticleTag.tag_id == tag.id)
    )
    return TagWithCountOut(id=tag.id, name=tag.name, article_count=int(count or 0))


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    tag = await _get_own_tag(session, user.id, tag_id)
    await session.delete(tag)  # article_tags 级联删除，卡片内容不受影响
    await session.commit()


@router.post("/merge", status_code=204)
async def merge_tags(
    body: TagMergeIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    if body.src_id == body.dst_id:
        raise err(C.VALIDATION_ERROR, "源标签与目标标签相同")
    await _get_own_tag(session, user.id, body.src_id)
    dst = await _get_own_tag(session, user.id, body.dst_id)
    # 关联迁移：合并后所有卡片挂到目标标签（幂等，冲突忽略）
    await session.execute(
        text(
            "INSERT INTO article_tags (article_id, tag_id) "
            "SELECT article_id, :dst FROM article_tags WHERE tag_id = :src "
            "ON CONFLICT DO NOTHING"
        ),
        {"src": body.src_id, "dst": dst.id},
    )
    src = await session.get(Tag, body.src_id)
    if src is not None:
        await session.delete(src)
    await session.commit()
