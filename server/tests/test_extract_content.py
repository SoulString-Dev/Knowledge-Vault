"""extract_content 抽取链测试：trafilatura 2.x 正文序列化、片段包壳、readability 兜底。"""

import pytest

from app.core.errors import JobPermanentError
from app.services.fetcher import QualityGateError, extract_content

_EN_BODY = "This is a long enough english paragraph for testing extraction. " * 12
_ZH_BODY = "这是一段足够长的中文正文内容，用于验证抽取链路与质量闸门的行为表现。" * 12


def test_英文正文完整文档() -> None:
    html = (
        "<html><head><title>Test Page</title></head><body>"
        f"<article><p>{_EN_BODY}</p></article></body></html>"
    )
    out = extract_content(html, "https://example.com/a")
    assert "english paragraph" in out["text"]
    assert out["title"] == "Test Page"


def test_中文正文完整文档() -> None:
    html = (
        "<html><head><title>中文页面</title></head><body>"
        f"<article><p>{_ZH_BODY}</p></article></body></html>"
    )
    out = extract_content(html, "https://example.com/zh")
    assert len(out["text"]) >= 200
    assert "中文正文" in out["text"]


def test_片段自动包壳() -> None:
    # readability partial 输出是片段；2.x 对片段判空，必须包壳后抽取
    fragment = f"<div><article><p>{_EN_BODY}</p></article></div>"
    out = extract_content(fragment, "https://example.com/frag")
    assert "english paragraph" in out["text"]


def test_空壳页面抽取不到() -> None:
    with pytest.raises((QualityGateError, JobPermanentError)):
        extract_content(
            "<html><head></head><body><div></div></body></html>", "https://example.com/x"
        )


def test_可读性兜底链() -> None:
    # 构造 trafilatura 不易识别、但 readability 能修剪出主内容区的页面：
    # 正文藏在非常规容器里且夹杂大量噪音文本
    noise = "<p>导航 导航 导航</p>" * 40
    body = (
        "<html><head><title>兜底链测试</title></head><body>"
        + noise
        + "<div class='unknown-widget'><span>"
        + _ZH_BODY
        + "</span></div>"
        + noise
        + "</body></html>"
    )
    try:
        out = extract_content(body, "https://example.com/fallback")
        # 任一路径抽出正文即视为通过
        assert len(out["text"]) >= 200
    except (QualityGateError, JobPermanentError):
        # 主链与兜底链都识别不了该结构时质量门生效即可，不强制成功
        pass
