"""中文分词：应用层 jieba → 'simple' tsvector / tsquery（ADR-2）。"""

from __future__ import annotations

import contextlib

import jieba

# to_tsvector 对超过 ~1MB（bytes）的输入会报错；中文 UTF-8 约 3 字节/字，取 20 万字符上限留足余量
TSV_CHARS_CAP = 200_000
# OR 匹配的词数上限：查询词过多会拖慢 tsquery 匹配
MAX_QUERY_TOKENS = 64

with contextlib.suppress(Exception):  # 收敛 jieba 建词典时的日志
    jieba.setLogLevel(60)


def tokenize(text: str) -> list[str]:
    return [t for t in jieba.cut_for_search(text) if t.strip()]


def build_tsvector_input(*parts: str | None) -> str:
    """标题 + 摘要 + 正文拼接后分词，空格连接写入 search_tsv。"""
    raw = "\n".join(p for p in parts if p)
    if not raw:
        return ""
    joined = " ".join(tokenize(raw))
    return joined[:TSV_CHARS_CAP]


def build_tsquery_or(query: str) -> str:
    """查询侧：分词后以 OR 连接，保证召回（避免 AND 语义零命中）。空串表示无法构造。"""
    tokens: list[str] = []
    for tok in tokenize(query):
        tok = tok.strip()
        if not tok or "'" in tok or tok in tokens:
            continue
        tokens.append(tok)
        if len(tokens) >= MAX_QUERY_TOKENS:
            break
    if not tokens:
        return ""
    return " | ".join(f"'{t}'" for t in tokens)
