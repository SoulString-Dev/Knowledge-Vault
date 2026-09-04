"""LLM 集成（架构文档 4.5）：OpenAI 兼容协议，集中一处便于 mock 与换厂商。"""

from __future__ import annotations

import asyncio
import json
import re
import string
from typing import Any

import openai
import structlog
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.core.errors import JobPermanentError, JobTransientError

log = structlog.get_logger()

_TEMPERATURE = 0.2
_MAX_TOKENS = 800  # 为 300 字摘要 + 8 标签留足余量，避免截断导致 JSON 解析失败
_SUMMARY_MAX_CHARS = 300
_TAGS_MAX = 8
_TAG_MAX_CHARS = 32
_CONTENT_PROMPT_CHARS = 12_000  # 与 4.4 长文裁剪策略一致
_ATTEMPTS = 3

_PROMPT_SYSTEM = "你是知识库系统的文章分析模块。仅输出一个 JSON 对象，不要输出任何其他文字。"
_REPAIR_PROMPT = (
    '你的输出不是合法 JSON。请只输出 JSON 对象：{"summary": "摘要", "tags": ["标签"]}。'
)


class LlmAnalysis(BaseModel):
    summary: str
    tags: list[str] = Field(default_factory=list)


def normalize_tag(raw: str) -> str:
    """tag 归一：去空白、去标点、长度截断。"""
    s = raw.strip()
    punct = set(string.punctuation) | set("，。、；：？！“”‘’（）《》〈〉【】·—…～￥%&*+=|\\/")
    s = "".join(ch for ch in s if ch not in punct)
    return re.sub(r"\s+", "", s)[:_TAG_MAX_CHARS]


def tag_key(tag: str) -> str:
    """复用比对键：小写 + 去标点（防同义标签碎片化，FR2.2）。"""
    return normalize_tag(tag).lower()


def parse_llm_json(raw: str) -> LlmAnalysis:
    """解析 LLM 输出：容忍代码围栏与前后杂讯；pydantic 校验 + 软截断。"""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("输出中未找到 JSON 对象")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是对象")
    out = LlmAnalysis.model_validate(data)
    summary = out.summary.strip()
    if not summary:
        raise ValueError("summary 为空")
    if len(summary) > _SUMMARY_MAX_CHARS:
        summary = summary[:_SUMMARY_MAX_CHARS]
    tags: list[str] = []
    seen: set[str] = set()
    for t in out.tags:
        nt = normalize_tag(str(t))
        if not nt:
            continue
        k = nt.lower()
        if k in seen:
            continue
        seen.add(k)
        tags.append(nt)
    return LlmAnalysis(summary=summary, tags=tags[:_TAGS_MAX])


def _client() -> openai.AsyncOpenAI:
    s = get_settings()
    return openai.AsyncOpenAI(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key.get_secret_value(),
        timeout=float(s.llm_timeout),
    )


def _user_prompt(title: str, content: str) -> str:
    return (
        "请为下面的文章生成中文摘要与关键词标签，仅输出 JSON："
        '{"summary": "100–300字中文摘要", "tags": ["关键词1", "关键词2"]}。\n'
        "要求：摘要 100–300 字中文；标签 3–8 个，使用通用、简洁的措辞，"
        "优先沿用常见说法，避免同义碎片化。\n\n"
        f"标题：{title}\n\n正文：\n{content[:_CONTENT_PROMPT_CHARS]}"
    )


async def _complete(
    messages: list[dict[str, str]], *, json_mode: bool
) -> openai.types.chat.ChatCompletion:
    s = get_settings()
    kwargs: dict[str, Any] = {
        "model": s.llm_model,
        "messages": messages,
        "temperature": _TEMPERATURE,
        "max_tokens": _MAX_TOKENS,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return await _client().chat.completions.create(**kwargs)  # type: ignore[arg-type]


async def summarize_and_tags(title: str, content_text: str) -> tuple[str, list[str]]:
    """摘要 + 打标：重试 3 次（指数退避）；解析失败发起一轮修复重问。"""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _PROMPT_SYSTEM},
        {"role": "user", "content": _user_prompt(title, content_text)},
    ]
    last_err: Exception | None = None
    for attempt in range(_ATTEMPTS):
        if attempt:
            await asyncio.sleep(min(2**attempt, 8))
        try:
            try:
                resp = await _complete(messages, json_mode=True)
            except openai.BadRequestError:
                # 部分兼容端点不支持 response_format，降级重试
                resp = await _complete(messages, json_mode=False)
            raw = resp.choices[0].message.content or ""
            try:
                out = parse_llm_json(raw)
            except (ValueError, json.JSONDecodeError, ValidationError):
                messages = [
                    *messages,
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": _REPAIR_PROMPT},
                ]
                last_err = ValueError("LLM 输出解析失败")
                continue
            return out.summary, out.tags
        except openai.AuthenticationError as e:
            raise JobPermanentError("LLM 认证失败：请检查 LLM_API_KEY") from e
        except openai.NotFoundError as e:
            raise JobPermanentError("LLM 模型不存在：请检查 LLM_MODEL") from e
        except openai.BadRequestError as e:
            raise JobPermanentError(f"LLM 请求被拒绝：{e}") from e
        except openai.APIConnectionError as e:  # 含超时
            last_err = e
        except openai.RateLimitError as e:
            last_err = e
        except openai.InternalServerError as e:
            last_err = e
    raise JobTransientError(f"LLM 调用失败：{last_err}")
