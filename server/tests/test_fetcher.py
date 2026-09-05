"""fetch_html 抓取行为测试：请求头、状态码分类、重试（MockTransport，不出网）。"""

import httpx
import pytest

from app.config import get_settings
from app.core.errors import JobPermanentError, JobTransientError
from app.services import fetcher as fetcher_mod
from app.services.fetcher import fetch_html


def _mock(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


async def test_发送浏览器UA与Accept头() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.headers))
        return httpx.Response(200, text="<html><body>ok</body></html>")

    html, final_url = await fetch_html("https://example.com/a", transport=_mock(handler))
    assert html == "<html><body>ok</body></html>"
    assert final_url == "https://example.com/a"
    # FR1.2：常规浏览器 UA；且带 Accept / Accept-Language
    assert "Chrome/" in seen["user-agent"]
    assert "compatible; KnowledgeVault" not in seen["user-agent"]
    assert seen["accept-language"].startswith("zh-CN")


async def test_404为永久失败() -> None:
    with pytest.raises(JobPermanentError) as exc:
        await fetch_html(
            "https://example.com/missing",
            transport=_mock(lambda request: httpx.Response(404, text="gone")),
        )
    assert "404" in str(exc.value)


async def test_403给出反爬处置提示() -> None:
    with pytest.raises(JobPermanentError) as exc:
        await fetch_html(
            "https://example.com/anti-bot",
            transport=_mock(lambda request: httpx.Response(403, text="blocked")),
        )
    assert "反爬" in str(exc.value)
    assert "PLAYWRIGHT_CDP_URL" in str(exc.value)


async def test_5xx重试后转为可重试错误() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, text="overloaded")

    settings = get_settings()
    original = settings.fetch_retries
    settings.fetch_retries = 2  # 显式 3 次尝试
    try:
        with pytest.raises(JobTransientError):
            await fetch_html("https://example.com/overload", transport=_mock(handler))
    finally:
        settings.fetch_retries = original
    assert calls["n"] == 3


async def test_重试后成功即返回() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500, text="boom")
        return httpx.Response(200, text="<html>recovered</html>")

    settings = get_settings()
    original = settings.fetch_retries
    settings.fetch_retries = 2
    try:
        # 跳过真实退避等待
        async def _no_sleep(_: float) -> None:
            return None

        original_sleep = fetcher_mod.asyncio.sleep
        fetcher_mod.asyncio.sleep = _no_sleep  # type: ignore[assignment]
        try:
            html, _ = await fetch_html("https://example.com/flaky", transport=_mock(handler))
        finally:
            fetcher_mod.asyncio.sleep = original_sleep
        assert html == "<html>recovered</html>"
        assert calls["n"] == 3
    finally:
        settings.fetch_retries = original


async def test_非HTML类型拒绝() -> None:
    with pytest.raises(JobPermanentError) as exc:
        await fetch_html(
            "https://example.com/file.pdf",
            transport=_mock(
                lambda request: httpx.Response(
                    200, content=b"%PDF-1.4", headers={"content-type": "application/pdf"}
                )
            ),
        )
    assert "Content-Type" in str(exc.value)
