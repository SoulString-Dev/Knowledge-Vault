"""管理员：用户管理（建号 / 禁用 / 重置密码 / 删除）与任务队列管理（F8）。"""

from __future__ import annotations

import re

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.errors import C, err
from app.core.security import hash_password
from app.db import get_session
from app.models import Job, RefreshToken, User
from app.schemas.admin import (
    AdminJobsOut,
    AdminUserCreateIn,
    AdminUserListOut,
    AdminUserOut,
    AdminUserPatchIn,
    JobOut,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])
log = structlog.get_logger()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


@router.get("/users", response_model=AdminUserListOut)
async def list_users(
    session: AsyncSession = Depends(get_session),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AdminUserListOut:
    total = await session.scalar(select(func.count()).select_from(User)) or 0
    rows = (
        await session.scalars(
            select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return AdminUserListOut(total=int(total), items=[AdminUserOut.model_validate(u) for u in rows])


@router.post("/users", response_model=AdminUserOut, status_code=201)
async def create_user(
    body: AdminUserCreateIn, session: AsyncSession = Depends(get_session)
) -> AdminUserOut:
    """建号（注册关闭模式使用，FR7.3 / FR8.1）：不走注册模式与邀请码检查。"""
    if not USERNAME_RE.fullmatch(body.username):
        raise err(C.VALIDATION_ERROR, "用户名仅允许 1–32 位字母、数字、_、-（不允许中文）")
    if await session.scalar(select(User.id).where(User.username == body.username)):
        raise err(C.USERNAME_TAKEN, "用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        is_admin=body.is_admin,
    )
    session.add(user)
    await session.commit()
    log.info("admin created user", username=body.username)
    return AdminUserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def patch_user(
    user_id: int,
    body: AdminUserPatchIn,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminUserOut:
    user = await session.get(User, user_id)
    if user is None:
        raise err(C.NOT_FOUND, "用户不存在")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise err(C.VALIDATION_ERROR, "没有需要修改的字段")
    if user.id == admin.id and changes.get("is_active") is False:
        raise err(C.INVALID_STATE, "不能禁用自己的账号")
    if user.id == admin.id and changes.get("is_admin") is False:
        raise err(C.INVALID_STATE, "不能移除自己的管理员权限")
    if "is_active" in changes:
        user.is_active = changes["is_active"]
    if "is_admin" in changes:
        user.is_admin = changes["is_admin"]
    if "new_password" in changes and changes["new_password"]:
        user.password_hash = hash_password(changes["new_password"])
        # 改密后吊销全部 refresh（ADR-5）
        await session.execute(
            update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
        )
    await session.commit()
    return AdminUserOut.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    if user_id == admin.id:
        raise err(C.INVALID_STATE, "不能删除自己的账号")
    user = await session.get(User, user_id)
    if user is None:
        raise err(C.NOT_FOUND, "用户不存在")
    await session.delete(user)  # 业务数据级联删除；快照文件由 worker 孤儿清扫兜底
    await session.commit()


@router.get("/jobs", response_model=AdminJobsOut)
async def jobs_overview(session: AsyncSession = Depends(get_session)) -> AdminJobsOut:
    stat_rows = await session.execute(select(Job.status, func.count()).group_by(Job.status))
    stats = {status: int(n) for status, n in stat_rows}
    failed = (
        await session.scalars(
            select(Job)
            .where(Job.status == "failed")
            .order_by(Job.finished_at.desc().nullslast(), Job.id.desc())
            .limit(50)
        )
    ).all()
    return AdminJobsOut(
        stats=stats,
        failed=[
            JobOut(
                id=j.id,
                type=j.type,
                status=j.status,
                attempts=j.attempts,
                max_attempts=j.max_attempts,
                article_id=j.article_id,
                error=j.error,
                created_at=j.created_at,
                finished_at=j.finished_at,
            )
            for j in failed
        ],
    )


@router.post("/jobs/{job_id}/retry", response_model=JobOut)
async def retry_job(job_id: int, session: AsyncSession = Depends(get_session)) -> JobOut:
    job = await session.get(Job, job_id)
    if job is None:
        raise err(C.NOT_FOUND, "任务不存在")
    if job.status != "failed":
        raise err(C.INVALID_STATE, "仅失败任务可重试")
    job.status = "queued"
    job.attempts = 0
    job.error = None
    job.locked_at = None
    job.finished_at = None
    await session.commit()
    return JobOut(
        id=job.id,
        type=job.type,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        article_id=job.article_id,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )
