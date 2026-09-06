"""应用配置：全部来自环境变量（或 server/.env），见架构文档 7.2。"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 安全
    secret_key: SecretStr  # 缺失时拒绝启动
    enable_docs: bool = False

    # 数据库与存储
    database_url: str = "postgresql+asyncpg://kb:kb@localhost:5432/kb"
    app_data_dir: str = "./app_data"  # 快照根目录（生产 /data/app）

    # 认证
    register_mode: Literal["open", "invite", "closed"] = "invite"
    invite_code: str | None = None
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    rate_limit_per_min: int = 5

    # LLM（OpenAI 兼容）
    llm_base_url: str
    llm_api_key: SecretStr
    llm_model: str
    llm_timeout: int = 60

    # Embedding（服务器本地推理；默认轻量档以满足 2GB 内存预算）
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dim: int = 512
    hf_endpoint: str | None = None

    # 抓取
    # 默认为较新版本的真实 Chrome UA（过旧的版本号会被部分站点区别对待）
    fetch_ua: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )
    fetch_timeout: int = 20
    fetch_retries: int = 2
    playwright_cdp_url: str | None = None
    # 渲染上下文注入登录 Cookie（"k=v; k2=v2"），用于知乎等要求登录态的站点；
    # 凭据留在自托管服务器，勿提交到仓库
    render_cookies: str | None = None
    render_cookies_domain: str | None = None  # 如 .zhihu.com
    # 多域注入（优先）：JSON 数组 [{"domain": ".zhihu.com", "cookies": "z_c0=…; d_c0=…"}, …]，
    # 渲染时按目标 URL 主机名自动匹配
    render_cookies_json: str | None = None

    # Worker
    worker_concurrency: int = 2
    job_zombie_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
