"""LLM 输出解析与标签归一测试。"""

import pytest

from app.services.llm import normalize_tag, parse_llm_json, tag_key


def test_parse_plain_json() -> None:
    out = parse_llm_json('{"summary": "摘要内容", "tags": ["Redis", "分布式"]}')
    assert out.summary == "摘要内容"
    assert out.tags == ["Redis", "分布式"]


def test_parse_fenced_json() -> None:
    raw = '```json\n{"summary": "s", "tags": ["a"]}\n```'
    assert parse_llm_json(raw).tags == ["a"]


def test_parse_json_with_prose() -> None:
    raw = '好的，结果如下：{"summary": "s", "tags": ["a"]} 以上。'
    assert parse_llm_json(raw).tags == ["a"]


def test_summary_soft_truncated() -> None:
    out = parse_llm_json('{"summary": "' + "长" * 400 + '", "tags": []}')
    assert len(out.summary) <= 300


def test_tags_normalized_dedup_capped() -> None:
    out = parse_llm_json(
        '{"summary": "s", "tags": ["Redis！", "redis ", "a' * 1
        + '", "", "b", "c", "d", "e", "f", "g", "h", "i"]}'
    )
    assert "Redis" in out.tags
    assert "" not in out.tags
    assert len(out.tags) <= 8


def test_tag_key_case_and_punct_insensitive() -> None:
    assert tag_key("Redis！") == tag_key("redis")
    assert tag_key(" 分布式 锁 ") == "分布式锁"


def test_parse_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_llm_json("这不是 JSON")
    with pytest.raises(ValueError):
        parse_llm_json('{"tags": ["a"]}')  # 缺 summary


def test_normalize_tag_strips_punct_and_space() -> None:
    assert normalize_tag("a" * 50) == "a" * 32
    assert normalize_tag("  分布式！ ") == "分布式"
