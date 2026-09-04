"""中文分词与 tsquery/tsvector 构造测试。"""

import pytest

from app.services.tokenizer_cn import (
    MAX_QUERY_TOKENS,
    TSV_CHARS_CAP,
    build_tsquery_or,
    build_tsvector_input,
    tokenize,
)


def test_tokenize_chinese() -> None:
    tokens = tokenize("分布式锁的坑")
    assert tokens and all(t.strip() for t in tokens)


def test_tsquery_or_format() -> None:
    tsq = build_tsquery_or("分布式锁的坑")
    assert tsq
    assert " | " in tsq
    assert tsq.startswith("'")
    # 'simple' 配置下词元用单引号包裹
    for part in tsq.split(" | "):
        assert part.startswith("'") and part.endswith("'")


def test_tsquery_dedup_and_cap() -> None:
    tsq = build_tsquery_or("锁 锁 锁 " + "锁 " * 200)
    assert tsq.count("'") // 2 <= MAX_QUERY_TOKENS


def test_tsquery_empty_for_no_tokens() -> None:
    assert build_tsquery_or("   ") == ""


def test_tsvector_input_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    # 绕过真实 jieba 分词（30 万字分词过慢），仅验证截断逻辑
    monkeypatch.setattr("app.services.tokenizer_cn.tokenize", lambda text: text.split()[:100_000])
    huge = "词 " * 300_000
    out = build_tsvector_input("标题", "摘要", huge)
    assert len(out) <= TSV_CHARS_CAP


def test_tsvector_input_empty_parts() -> None:
    assert build_tsvector_input(None, "", None) == ""
