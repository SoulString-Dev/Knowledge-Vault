"""Embedding（架构文档 4.6）：sentence-transformers 进程内懒加载单例。

worker 承担文档向量化；语义检索时 api 侧对查询词向量化的说明见模块底部注释。
"""

from __future__ import annotations

import asyncio

import structlog

from app.config import get_settings
from app.core.errors import JobPermanentError

log = structlog.get_logger()

_EMBED_BATCH_SIZE = 32  # 重嵌入按批 32 条
_INPUT_CHARS_CAP = 12_000  # 与 4.4 长文裁剪策略一致


def build_embed_input(title: str | None, summary: str | None, content: str | None) -> str:
    """输入拼接：标题 → 摘要 → 正文，截断至 ~12k 字符（ADR-3）。"""
    parts = [p for p in (title, summary, content) if p]
    return "\n".join(parts)[:_INPUT_CHARS_CAP]


class _Model:
    _model: object | None = None
    _lock = asyncio.Lock()


async def _get_model() -> object:
    if _Model._model is None:
        async with _Model._lock:
            if _Model._model is None:
                s = get_settings()

                def load() -> object:
                    try:
                        from sentence_transformers import SentenceTransformer
                    except ImportError as e:
                        raise JobPermanentError(
                            "未安装 embedding 依赖：请在部署镜像或本地执行 uv sync --extra embed"
                        ) from e
                    log.info("loading embedding model", model=s.embedding_model)
                    return SentenceTransformer(s.embedding_model, device="cpu")

                _Model._model = await asyncio.to_thread(load)
                log.info("embedding model ready", model=s.embedding_model)
    return _Model._model


async def preload() -> None:
    """worker 启动时预热加载（首次含 ~2.3GB 模型下载，日志给进度提示）。"""
    await _get_model()


async def encode_batch(texts: list[str]) -> list[list[float]]:
    """批量向量化，输出 L2 归一化向量（检索用余弦相似度）。"""
    if not texts:
        return []
    model = await _get_model()

    def run() -> list[list[float]]:
        return model.encode(  # type: ignore[attr-defined]
            texts,
            batch_size=_EMBED_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    # 模型 encode 非线程安全，用锁串行化并发调用
    async with _Model._lock:
        return await asyncio.to_thread(run)


async def encode_one(text: str) -> list[float]:
    return (await encode_batch([text]))[0]


# 设计说明：架构文档 4.6 写「api 不加载模型」，但 8.2 的语义检索读路径要求
# api 对查询词向量化——两者矛盾。此处按读路径实现：api 进程首次执行
# semantic/hybrid 检索时懒加载同一模型。内存影响：bge-m3 双进程约需 6GB；
# 4GB 机器建议 EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5（512 维，需重嵌入）。
