"""网页抓取与正文抽取（架构文档 4.4）+ URL 规范化 + 快照文件管理。"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import gzip
import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import charset_normalizer
import httpx
import structlog

from app.config import get_settings
from app.core.errors import AntiBotBlockedError, C, JobPermanentError, JobTransientError, err

log = structlog.get_logger()

# 已知跟踪参数（v1.2 规范化规则；如需扩展在此追加）
_TRACKING_PARAM_RE = re.compile(
    r"^(utm_\w+|spm|fbclid|gclid|igshid|vdsource|share_source|share_medium|fr|refer_from)$",
    re.IGNORECASE,
)
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_MIN_CONTENT_CHARS = 200  # 质量闸门（4.4 第 4 步）


# ---------- URL 规范化（v1.2 规则表） ----------


def normalize_url(raw: str) -> str:
    """规则：scheme 缺失补 https 且 http/https 视为同一 URL；host 小写；
    默认端口省略；去 fragment；移除跟踪参数；query 按参数名排序；路径末尾斜杠等价。"""
    url = raw.strip()
    if not url:
        raise err(C.VALIDATION_ERROR, "URL 不能为空")
    if len(url) > 2048:
        raise err(C.VALIDATION_ERROR, "URL 过长")
    if not _SCHEME_RE.match(url):
        url = "https://" + url
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if ":" in host:
        h, _, port = host.rpartition(":")
        if port.isdigit() and port in {"80", "443"}:
            host = h
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _TRACKING_PARAM_RE.match(k)
    ]
    kept.sort(key=lambda kv: kv[0])
    return urlunsplit(("https", host, path, urlencode(kept), ""))


def url_hash(clean_url: str) -> str:
    return hashlib.sha256(clean_url.encode("utf-8")).hexdigest()


def host_of(clean_url: str) -> str | None:
    return urlsplit(clean_url).hostname


# ---------- 抓取 ----------


def decode_html(data: bytes, content_type: str) -> str:
    """编码判定顺序：HTTP 头 → <meta charset> → 自动检测（4.4 第 2 步）。"""
    m = re.search(r"charset=([A-Za-z0-9_-]+)", content_type or "", re.IGNORECASE)
    if m:
        try:
            return data.decode(m.group(1))
        except (LookupError, UnicodeDecodeError):
            pass
    meta = re.search(rb"<meta[^>]+charset=[\"']?([a-za-z0-9_-]+)", data[:4096].lower())
    if meta:
        try:
            return data.decode(meta.group(1).decode("ascii"))
        except (LookupError, UnicodeDecodeError):
            pass
    best = charset_normalizer.from_bytes(data).best()
    if best is not None:
        return str(best)
    return data.decode("utf-8", errors="replace")


# 与常规浏览器一致的请求头（FR1.2）：自报家门的爬虫 UA 会被大量站点直接 403
_BROWSER_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def fetch_html(
    url: str, *, transport: httpx.AsyncBaseTransport | None = None
) -> tuple[str, str]:
    """抓取：常规浏览器 UA 与请求头、跟随重定向、超时与自动重试。返回 (html, 最终 url)。

    4xx（除 429）视为永久失败；5xx / 429 / 网络错误重试后抛 JobTransientError。
    transport 参数仅供测试注入（httpx.MockTransport）。
    """
    s = get_settings()
    last: Exception | None = None
    for attempt in range(s.fetch_retries + 1):
        if attempt:
            await asyncio.sleep(min(2**attempt, 8))
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=float(s.fetch_timeout),
                headers={"User-Agent": s.fetch_ua, **_BROWSER_HEADERS},
                transport=transport,
            ) as client:
                resp = await client.get(url)
            if resp.status_code >= 500 or resp.status_code == 429:
                last = RuntimeError(f"HTTP {resp.status_code}")
                continue
            if resp.status_code >= 400:
                if resp.status_code == 403:
                    raise AntiBotBlockedError(
                        "目标站点反爬拦截（HTTP 403）：该站点可能需要浏览器执行 JS 挑战，"
                        "可在服务端配置 JS 渲染兜底（PLAYWRIGHT_CDP_URL + render profile）后重试，"
                        "或使用手动粘贴文本补救"
                    )
                raise JobPermanentError(f"目标页面返回 HTTP {resp.status_code}")
            content_type = resp.headers.get("content-type", "")
            if content_type and not content_type.lower().startswith(
                ("text/html", "application/xhtml", "text/plain")
            ):
                raise JobPermanentError(
                    f"不支持的 Content-Type：{content_type.split(';')[0].strip()}"
                )
            return decode_html(resp.content, content_type), str(resp.url)
        except JobPermanentError:
            raise
        except httpx.HTTPError as e:
            last = e
    raise JobTransientError(f"抓取失败：{last}")


# ---------- 正文抽取 ----------


class QualityGateError(Exception):
    """抽取结果不足 200 字符（质量闸门），可走 JS 渲染兜底后重抽。"""


def _doc_get(doc: object, key: str, default: str | None = None) -> str | None:
    """trafilatura bare_extraction 新版返回 Document、旧版返回 dict。"""
    value = doc.get(key, default) if isinstance(doc, dict) else getattr(doc, key, default)
    return value if value is None else str(value)


def _wrap_fragment(html: str) -> str:
    """trafilatura 2.x 对缺少完整文档结构的片段判空：统一包壳。"""
    if "<html" in html[:500].lower():
        return html
    return '<html><head><meta charset="utf-8"></head><body>' + html + "</body></html>"


def _trafilatura_extract(html: str, url: str) -> tuple[str | None, object | None]:
    """正文（markdown，经 extract() 序列化——2.x 的 bare_extraction 不产出 text 字段）
    + 元数据（bare_extraction 的 Document）。"""
    from trafilatura import bare_extraction, extract

    wrapped = _wrap_fragment(html)
    meta = bare_extraction(
        wrapped,
        url=url,
        favor_recall=True,
        with_metadata=True,
        include_tables=True,
    )
    text = extract(
        wrapped,
        url=url,
        favor_recall=True,
        output_format="markdown",
        include_tables=True,
        include_images=False,
        include_links=False,
    )
    return (text.strip() if text else None), meta


def _readability_extract(html: str) -> str | None:
    """readability-lxml 修剪主内容区（3.1 预留的兜底）：返回修剪后的完整 HTML 或 None。"""
    try:
        from readability import Document as ReadabilityDocument
    except ImportError:
        return None
    try:
        summary = ReadabilityDocument(html).summary(html_partial=False)
    except Exception:
        return None
    if summary and len(summary) > _MIN_CONTENT_CHARS:
        return summary
    return None


def extract_content(html: str, url: str) -> dict[str, str | None]:
    """正文抽取：trafilatura 优先；不足时用 readability 修剪主内容区再交给
    trafilatura（B站图文等特殊 DOM 的兜底链，架构文档 3.1）。"""
    try:
        text, meta = _trafilatura_extract(html, url)
    except Exception as e:  # 抽取器崩溃按永久失败处理
        raise JobPermanentError(f"正文抽取异常：{e}") from e

    best_text = (text or "").strip()
    if len(best_text) < _MIN_CONTENT_CHARS:
        cleaned = _readability_extract(html)
        if cleaned:
            try:
                text2, meta2 = _trafilatura_extract(cleaned, url)
            except Exception as e:  # pragma: no cover - 二次抽取崩溃同样按永久失败
                raise JobPermanentError(f"正文抽取异常：{e}") from e
            if text2 and len(text2.strip()) > len(best_text):
                best_text, meta = text2.strip(), meta2

    if not best_text:
        raise JobPermanentError("未能抽取到正文")
    if len(best_text) < _MIN_CONTENT_CHARS:
        raise QualityGateError(f"正文过短（{len(best_text)} 字符）")
    return {
        "title": _doc_get(meta, "title"),
        "author": _doc_get(meta, "author"),
        "date": _doc_get(meta, "date"),
        "language": _doc_get(meta, "language"),
        "text": best_text,
    }


def md_to_text(md: str) -> str:
    """Markdown → 纯文本的粗转换（检索 / LLM 输入用，不追求完美）。"""
    text = re.sub(r"```.*?```", " ", md, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_`~]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_published_at(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)
    except ValueError:
        return None


async def render_with_cdp(url: str) -> str:
    """JS 渲染兜底：经 CDP 连接 browserless（仅配置 PLAYWRIGHT_CDP_URL 时启用）。"""
    s = get_settings()
    if not s.playwright_cdp_url:
        raise JobPermanentError("未配置 JS 渲染兜底（PLAYWRIGHT_CDP_URL）")
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise JobPermanentError(
            "已配置 PLAYWRIGHT_CDP_URL 但未安装 playwright（uv sync --extra render）"
        ) from e
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(s.playwright_cdp_url)
            context = await browser.new_context(user_agent=s.fetch_ua)
            if s.render_cookies:
                if not s.render_cookies_domain:
                    raise JobPermanentError(
                        "配置了 RENDER_COOKIES 但缺少 RENDER_COOKIES_DOMAIN（如 .zhihu.com）"
                    )
                cookies = [
                    {
                        "name": pair.split("=", 1)[0].strip(),
                        "value": pair.split("=", 1)[1].strip(),
                        "domain": s.render_cookies_domain,
                        "path": "/",
                    }
                    for pair in s.render_cookies.split(";")
                    if "=" in pair
                ]
                if cookies:
                    await context.add_cookies(cookies)
                    log.info(
                        "render cookies injected",
                        domain=s.render_cookies_domain,
                        count=len(cookies),
                    )
            page = await context.new_page()
            try:
                await page.goto(url, timeout=s.fetch_timeout * 1000, wait_until="domcontentloaded")
                # SPA / 反爬挑战需要执行时间：优先等网络空闲，超时则以已渲染内容继续
                with contextlib.suppress(Exception):
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                await page.wait_for_timeout(1_500)
                html = await page.content()
                trimmed = html.lstrip()
                if trimmed.startswith("{") and '"error"' in trimmed[:400]:
                    # 站点直接吐 JSON 错误（如知乎 40362）：渲染通道没问题，缺登录态/被风控
                    raise JobPermanentError(
                        f"渲染后站点仍返回错误响应（需要配置 RENDER_COOKIES 注入登录 Cookie，"
                        f"或已触发站点风控）：{trimmed[:200]}"
                    )
                # 渲染产物可观测：长度/标题进日志，便于诊断"渲染拿到的是什么"
                log.info(
                    "render fallback captured",
                    url=url,
                    html_len=len(html),
                    title=(await page.title())[:120],
                )
                return html
            finally:
                await context.close()
                await browser.close()
    except JobPermanentError:
        raise
    except Exception as e:
        raise JobTransientError(f"JS 渲染兜底失败：{e}") from e


# ---------- 快照文件（先库后文件，孤儿由 worker 定期清扫） ----------


def save_snapshot(user_id: int, article_id: int, html: str) -> str:
    s = get_settings()
    base = Path(s.app_data_dir)
    rel = f"snapshots/{user_id}/{article_id}.html.gz"
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(html.encode("utf-8", errors="replace")))
    return rel


def save_render_debug(article_id: int, html: str) -> str | None:
    """渲染兜底抽取失败时落盘 HTML 供排查；落盘失败不影响主流程。"""
    try:
        base = Path(get_settings().app_data_dir)
        debug_dir = base / "render_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        ts = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
        path = debug_dir / f"{article_id}-{ts}.html"
        path.write_text(html, encoding="utf-8")
        return str(path)
    except OSError:
        return None


def delete_snapshot_file(rel_path: str | None) -> None:
    if not rel_path:
        return
    base = Path(get_settings().app_data_dir).resolve()
    try:
        path = (base / rel_path).resolve()
        if path.is_relative_to(base):
            path.unlink(missing_ok=True)
    except OSError as e:  # 删除失败留孤儿，由定期清扫兜底
        log.warning("snapshot delete failed", path=rel_path, error=str(e))


def resolve_snapshot_path(rel_path: str) -> Path:
    base = Path(get_settings().app_data_dir).resolve()
    path = (base / rel_path).resolve()
    if not path.is_relative_to(base):
        raise err(C.NOT_FOUND, "快照路径非法")
    return path
