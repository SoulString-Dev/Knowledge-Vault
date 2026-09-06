"""渲染 Cookie 选择与风控页识别测试（样本来自知乎 JSON 403 与 B站验证码页实测）。"""

import pytest

from app.config import get_settings
from app.core.errors import JobPermanentError
from app.services.fetcher import _detect_render_block, _host_matches, _select_cookies_for

BILI_CAPTCHA_HTML = (
    '<!DOCTYPE html><html><head><meta charset="UTF-8">'
    "<title>验证码_哔哩哔哩</title></head>"
    "<body><div class='risk-captcha'>captcha</div></body></html>"
)
ZHIHU_JSON_ERROR = '{"error":{"message":"您当前请求存在异常，暂时限制本次访问。","code":40362}}'


def _settings(**overrides: str) -> object:
    s = get_settings()
    s.render_cookies = overrides.get("render_cookies")
    s.render_cookies_domain = overrides.get("render_cookies_domain")
    s.render_cookies_json = overrides.get("render_cookies_json")
    return s


def test_host_matches() -> None:
    assert _host_matches("www.zhihu.com", ".zhihu.com")
    assert _host_matches("zhihu.com", "zhihu.com")
    assert _host_matches("www.bilibili.com", ".bilibili.com")
    assert not _host_matches("www.bilibili.com", ".zhihu.com")
    assert not _host_matches("www.zhihu.com", "")
    assert not _host_matches("", ".zhihu.com")


def test_json_多域按主机名匹配() -> None:
    s = _settings(
        render_cookies_json=(
            '[{"domain": ".zhihu.com", "cookies": "z_c0=2|1:0|abc; d_c0=def"},'
            ' {"domain": ".bilibili.com", "cookies": "SESSDATA=xyz; buvid3=u3"}]'
        )
    )
    zhihu = _select_cookies_for("https://www.zhihu.com/question/1", s)
    assert {c["name"] for c in zhihu} == {"z_c0", "d_c0"}
    assert all(c["domain"] == ".zhihu.com" for c in zhihu)
    # 值里的 | 与后续 = 不破坏解析
    assert next(c for c in zhihu if c["name"] == "z_c0")["value"] == "2|1:0|abc"

    bili = _select_cookies_for("https://www.bilibili.com/opus/123", s)
    assert {c["name"] for c in bili} == {"SESSDATA", "buvid3"}


def test_单域配置不匹配时不注入() -> None:
    s = _settings(render_cookies="z_c0=abc", render_cookies_domain=".zhihu.com")
    assert _select_cookies_for("https://www.bilibili.com/opus/1", s) == []
    assert _select_cookies_for("https://www.zhihu.com/q", s)


def test_单域缺domain时显式报错() -> None:
    s = _settings(render_cookies="z_c0=abc", render_cookies_domain=None)
    with pytest.raises(JobPermanentError):
        _select_cookies_for("https://www.zhihu.com/q", s)


def test_非法JSON报永久错误() -> None:
    s = _settings(render_cookies_json="not-json")
    with pytest.raises(JobPermanentError):
        _select_cookies_for("https://www.zhihu.com/q", s)


def test_识别B站验证码页() -> None:
    reason = _detect_render_block(BILI_CAPTCHA_HTML)
    assert reason is not None
    assert "RENDER_COOKIES_JSON" in reason


def test_识别知乎JSON错误页() -> None:
    reason = _detect_render_block(ZHIHU_JSON_ERROR)
    assert reason is not None
    assert "Cookie" in reason


def test_正常页面不误报() -> None:
    normal = (
        "<html><head><title>正常文章</title></head><body>"
        '<p>正文内容，包含 {"error":} 之类的花括号也不会误判。</p></body></html>'
    )
    assert _detect_render_block(normal) is None
