"""API 集成测试：需要真实 PostgreSQL（pgvector + pg_trgm）。

本地未配置数据库时自动跳过；CI 中由 pgvector/pgvector:pg16 service container 提供。
服务边界全部打桩（抓取 / LLM / embedding），不依赖外网与真实模型。
"""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import auth as auth_mod
from app.config import get_settings
from app.core.errors import AntiBotBlockedError
from app.core.ratelimit import SlidingWindowLimiter
from app.core.security import hash_password
from app.db import Base, get_session
from app.main import create_app
from app.models import Article, Job, User
from app.services import embedder as embedder_mod
from app.services import llm as llm_mod
from app.workers import handlers as handlers_mod

DB_URL = get_settings().database_url


async def _db_reachable() -> bool:
    try:
        engine = create_async_engine(DB_URL, pool_pre_ping=True)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def db_engine():
    if not await _db_reachable():
        pytest.skip(
            "数据库不可用，跳过集成测试（CI 中由 pgvector 容器提供）", allow_module_level=False
        )
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def stub_services(monkeypatch: pytest.MonkeyPatch):
    """打桩：LLM 分析与 embedding 不依赖外部服务。"""

    async def fake_summarize(title: str, content: str) -> tuple[str, list[str]]:
        return f"{title} 的摘要（测试桩）", ["测试标签", "集成测试"]

    async def fake_encode(texts: list[str]) -> list[list[float]]:
        return [[0.1] * get_settings().embedding_dim for _ in texts]

    async def fake_fetch(url: str) -> tuple[str, str]:
        html = (
            "<html><head><title>测试文章标题</title></head><body>"
            + "<p>"
            + "这是一段足够长的测试正文内容，" * 60
            + "</p></body></html>"
        )
        return html, url

    def fake_extract(html: str, url: str) -> dict[str, str]:
        return {
            "title": "测试文章标题",
            "author": "测试作者",
            "date": "2026-09-05T00:00:00+00:00",
            "language": "zh",
            "text": "这是一段足够长的测试正文内容，用于验证采集流水线。" * 30,
        }

    monkeypatch.setattr(llm_mod, "summarize_and_tags", fake_summarize)
    monkeypatch.setattr(embedder_mod, "encode_batch", fake_encode)
    monkeypatch.setattr(handlers_mod, "fetch_html", fake_fetch)
    monkeypatch.setattr(handlers_mod, "extract_content", fake_extract)
    # 集成测试共享同一客户端 IP，替换为大额度限速器避免 429 干扰
    monkeypatch.setattr(auth_mod, "_limiter", SlidingWindowLimiter(100_000))


async def _run_jobs_tolerant(factory) -> None:
    """手动执行排队任务；handler 失败时标记 failed 并继续（用于验证失败路径）。"""
    from sqlalchemy import func as sa_func
    from sqlalchemy import update

    from app.workers.runner import CLAIM_SQL

    while True:
        async with factory() as session:
            row = (await session.execute(CLAIM_SQL)).mappings().first()
            if row is None:
                return
            job = handlers_mod.JobView(row)
            try:
                await handlers_mod.HANDLERS[job.type](session, job)
                await session.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(status="done", finished_at=sa_func.now())
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                async with factory() as s2:
                    # 与真实 runner 语义一致：job 最终失败 → 同步把 article 置为 failed
                    await s2.execute(
                        update(Job)
                        .where(Job.id == job.id)
                        .values(
                            status="failed",
                            error=str(e)[:2000],
                            attempts=99,
                            finished_at=sa_func.now(),
                        )
                    )
                    await s2.execute(
                        update(Article)
                        .where(
                            Article.id == job.article_id,
                            Article.status.in_(["pending", "processing"]),
                        )
                        .values(status="failed", error=str(e)[:2000])
                    )
                    await s2.commit()


async def _register(client: httpx.AsyncClient, username: str | None = None) -> dict:
    username = username or f"u{uuid.uuid4().hex[:10]}"
    resp = await client.post(
        "/api/v1/auth/register", json={"username": username, "password": "password123"}
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _run_queued_jobs(factory) -> None:
    """手动执行所有排队任务（不启动 runner 循环）。"""
    from sqlalchemy import func as sa_func
    from sqlalchemy import update

    from app.workers.runner import CLAIM_SQL

    while True:
        async with factory() as session:
            row = (await session.execute(CLAIM_SQL)).mappings().first()
            if row is None:
                return
            job = handlers_mod.JobView(row)
            handler = handlers_mod.HANDLERS[job.type]
            try:
                await handler(session, job)
                await session.execute(
                    update(Job)
                    .where(Job.id == job.id)
                    .values(status="done", finished_at=sa_func.now())
                )
                await session.commit()
            except Exception:
                await session.rollback()
                async with factory() as s2:
                    await s2.execute(
                        update(Job)
                        .where(Job.id == job.id)
                        .values(status="failed", error="test", finished_at=sa_func.now())
                    )
                    await s2.commit()
                raise


async def test_healthz_readyz(client: httpx.AsyncClient) -> None:
    assert (await client.get("/healthz")).status_code == 200
    resp = await client.get("/readyz")
    assert resp.status_code == 200


async def test_register_login_me(client: httpx.AsyncClient) -> None:
    tokens = await _register(client)
    headers = await _auth_headers(tokens)
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    # 首个注册用户是管理员
    assert me.json()["is_admin"] is True

    # refresh 轮换
    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    # 旧 refresh 复用 → 全部吊销
    reused = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reused.status_code == 401
    assert reused.json()["code"] == "REFRESH_REUSED"


async def test_second_user_not_admin(client: httpx.AsyncClient) -> None:
    await _register(client)
    tokens2 = await _register(client)
    me = await client.get("/api/v1/auth/me", headers=await _auth_headers(tokens2))
    assert me.json()["is_admin"] is False


async def test_full_pipeline_paste_search(client: httpx.AsyncClient, db_engine) -> None:
    tokens = await _register(client)
    headers = await _auth_headers(tokens)
    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    # 粘贴建卡 → analyze → embed → ready
    resp = await client.post(
        "/api/v1/articles/paste",
        headers=headers,
        json={"title": "粘贴测试", "text": "这是粘贴的一段足够长的测试文本内容。" * 20},
    )
    assert resp.status_code == 202, resp.text
    article_id = resp.json()["id"]

    await _run_queued_jobs(factory)
    detail = await client.get(f"/api/v1/articles/{article_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "ready"
    assert body["summary"]
    assert [t["name"] for t in body["tags"]] == ["测试标签", "集成测试"]

    # 关键词检索（tsvector 已写入）
    kw = await client.post(
        "/api/v1/search", headers=headers, json={"query": "粘贴 测试", "mode": "keyword"}
    )
    assert kw.status_code == 200
    assert any(r["article_id"] == article_id for r in kw.json()["results"])

    # 语义与混合检索（embedding 为桩向量）
    sem = await client.post(
        "/api/v1/search", headers=headers, json={"query": "任意查询", "mode": "semantic"}
    )
    assert sem.status_code == 200
    assert sem.json()["results"]
    hybrid = await client.post(
        "/api/v1/search", headers=headers, json={"query": "粘贴", "mode": "hybrid"}
    )
    assert hybrid.status_code == 200
    top = hybrid.json()["results"][0]
    assert top["matched_by"]


async def test_url_dedup_and_isolation(client: httpx.AsyncClient, db_engine) -> None:
    tokens1 = await _register(client)
    headers1 = await _auth_headers(tokens1)
    url = "https://example.com/post/123?utm_source=x"

    r1 = await client.post("/api/v1/articles", headers=headers1, json={"url": url})
    assert r1.status_code == 202
    r2 = await client.post("/api/v1/articles", headers=headers1, json={"url": url})
    assert r2.status_code == 200  # 重复：返回旧卡
    assert r2.json()["id"] == r1.json()["id"]

    # 用户隔离：用户 2 看不到用户 1 的卡片
    tokens2 = await _register(client)
    headers2 = await _auth_headers(tokens2)
    detail = await client.get(f"/api/v1/articles/{r1.json()['id']}", headers=headers2)
    assert detail.status_code == 404
    lst = await client.get("/api/v1/articles", headers=headers2)
    assert lst.json()["total"] == 0


async def test_patch_triggers_reindex_and_embed(client: httpx.AsyncClient, db_engine) -> None:
    tokens = await _register(client)
    headers = await _auth_headers(tokens)
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    resp = await client.post(
        "/api/v1/articles/paste", headers=headers, json={"text": "待修正的正文内容。" * 30}
    )
    article_id = resp.json()["id"]
    await _run_queued_jobs(factory)

    patched = await client.patch(
        f"/api/v1/articles/{article_id}", headers=headers, json={"summary": "人工修正的摘要"}
    )
    assert patched.status_code == 200
    await _run_queued_jobs(factory)
    async with factory() as session:
        article = await session.get(Article, article_id)
        assert article is not None
        assert article.summary == "人工修正的摘要"
        assert article.status == "ready"
        assert article.search_tsv is not None


async def test_admin_user_management(client: httpx.AsyncClient, db_engine) -> None:
    # 共享库中注册顺序不可控，直接造一个管理员验证 admin 通道
    admin_user = User(
        username=f"root{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        session.add(admin_user)
        await session.commit()
    login = await client.post(
        "/api/v1/auth/login", json={"username": admin_user.username, "password": "password123"}
    )
    assert login.status_code == 200
    headers1 = await _auth_headers(login.json())
    tokens2 = await _register(client)
    me2 = (await client.get("/api/v1/auth/me", headers=await _auth_headers(tokens2))).json()

    # 建号
    created = await client.post(
        "/api/v1/admin/users",
        headers=headers1,
        json={"username": f"admin{uuid.uuid4().hex[:6]}", "password": "password123"},
    )
    assert created.status_code == 201

    # 普通用户访问 admin → 403
    forbidden = await client.get("/api/v1/admin/users", headers=await _auth_headers(tokens2))
    assert forbidden.status_code == 403

    # 禁用用户 2 → 其 access 立即不可用（get_current_user 校验 is_active）
    patched = await client.patch(
        f"/api/v1/admin/users/{me2['id']}", headers=headers1, json={"is_active": False}
    )
    assert patched.status_code == 200
    denied = await client.get("/api/v1/auth/me", headers=await _auth_headers(tokens2))
    assert denied.status_code == 403

    # 任务队列统计端点可用
    jobs = await client.get("/api/v1/admin/jobs", headers=headers1)
    assert jobs.status_code == 200
    assert "stats" in jobs.json()


async def test_refresh_reuse_revokes_all(client: httpx.AsyncClient) -> None:
    tokens = await _register(client)
    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != tokens["refresh_token"]
    # 再次用旧 refresh → 触发盗用检测
    reused = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reused.status_code == 401
    # 新 refresh 也已被连带吊销
    with_new = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert with_new.status_code == 401


async def test_extract_falls_back_to_render_on_antibot(
    client: httpx.AsyncClient, db_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """抓取被反爬拦截（403）且配置了渲染兜底：自动转 browserless 渲染重抽并完成流水线。"""
    settings = get_settings()
    original_cdp = settings.playwright_cdp_url
    settings.playwright_cdp_url = "ws://render:3000?token=kb-render"

    async def blocked_fetch(url: str) -> tuple[str, str]:
        raise AntiBotBlockedError("目标站点反爬拦截（HTTP 403）")

    rendered_html = (
        "<html><head><title>渲染后的标题</title></head><body>"
        + "<p>"
        + "这是浏览器渲染得到的足够长的正文内容，" * 40
        + "</p></body></html>"
    )

    async def fake_render(url: str) -> str:
        return rendered_html

    def fake_extract_rendered(html: str, url: str) -> dict[str, str]:
        return {
            "title": "渲染后的标题",
            "author": "测试作者",
            "date": "2026-09-05T00:00:00+00:00",
            "language": "zh",
            "text": "这是浏览器渲染得到的足够长的正文内容，用于验证渲染兜底链路。" * 30,
        }

    monkeypatch.setattr(handlers_mod, "fetch_html", blocked_fetch)
    monkeypatch.setattr(handlers_mod, "render_with_cdp", fake_render)
    # 覆盖 autouse 桩：渲染路径的抽取结果应来自渲染后的 HTML
    monkeypatch.setattr(handlers_mod, "extract_content", fake_extract_rendered)
    try:
        tokens = await _register(client)
        headers = await _auth_headers(tokens)
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        resp = await client.post(
            "/api/v1/articles", headers=headers, json={"url": "https://blocked.example.com/a"}
        )
        assert resp.status_code == 202
        article_id = resp.json()["id"]

        await _run_jobs_tolerant(factory)

        detail = await client.get(f"/api/v1/articles/{article_id}", headers=headers)
        body = detail.json()
        assert body["status"] == "ready", body.get("error")
        assert body["title"] == "渲染后的标题"
    finally:
        settings.playwright_cdp_url = original_cdp


async def test_reanalyze_rejected_when_no_content(
    client: httpx.AsyncClient, db_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """抓取失败（403 且无渲染兜底）→ failed；reanalyze 应 409 引导走重试；retry 重新入队抓取。"""
    settings = get_settings()
    original_cdp = settings.playwright_cdp_url
    settings.playwright_cdp_url = None

    async def blocked_fetch(url: str) -> tuple[str, str]:
        raise AntiBotBlockedError("目标站点反爬拦截（HTTP 403）")

    monkeypatch.setattr(handlers_mod, "fetch_html", blocked_fetch)
    try:
        tokens = await _register(client)
        headers = await _auth_headers(tokens)
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        resp = await client.post(
            "/api/v1/articles", headers=headers, json={"url": "https://blocked.example.com/b"}
        )
        article_id = resp.json()["id"]
        await _run_jobs_tolerant(factory)

        detail = await client.get(f"/api/v1/articles/{article_id}", headers=headers)
        assert detail.json()["status"] == "failed"
        assert "反爬" in (detail.json()["error"] or "")

        # 无正文的卡片不允许重新分析
        r = await client.post(f"/api/v1/articles/{article_id}/reanalyze", headers=headers)
        assert r.status_code == 409
        assert r.json()["code"] == "INVALID_STATE"

        # retry（无文本）→ 重新入队 extract → 再次失败（仍 403）
        retry = await client.post(f"/api/v1/articles/{article_id}/retry", headers=headers, json={})
        assert retry.status_code == 200
    finally:
        settings.playwright_cdp_url = original_cdp
