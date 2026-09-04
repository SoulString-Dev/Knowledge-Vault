# 知识匣（Knowledge Vault）

自托管的跨平台 AI 知识库：收藏网页 → LLM 自动摘要打标 → 多端检索、阅读、批注。

> 当前处于**设计阶段**，仓库中暂只有设计文档，尚未开始编码。

## 文档索引

| 文档 | 内容 |
|---|---|
| [01-需求规格说明书](docs/01-需求规格说明书.md) | 项目概述、功能需求（F1–F8）、非功能需求、里程碑、验收清单 |
| [02-架构设计说明书](docs/02-架构设计说明书.md) | 总体架构、技术选型与 ADR、数据库 DDL、任务流水线、API 设计、客户端设计、部署方案 |

## 已确认的关键决策

- 客户端：**Flutter** 一套代码（Android + Windows/macOS/Linux）
- LLM：**OpenAI 兼容协议**，环境变量切换厂商（DeepSeek/Qwen/GLM/OpenAI/Ollama…）
- 语义检索：服务器**本地 bge-m3** embedding（文本不出服务器）
- 用户体系：**多用户**（bcrypt + JWT，数据按 user_id 隔离，首个用户为管理员）
- 基础设施：**FastAPI + PostgreSQL(pgvector)** + PG 任务表队列，Docker Compose 三容器（api / worker / db）部署

## 规划的仓库结构

```
Knowledge-Vault/
├── server/    # FastAPI 服务端（api + worker 同镜像）
├── client/    # Flutter 客户端
├── deploy/    # docker-compose、.env、备份脚本
└── docs/      # 设计文档
```

## 开发（M1 服务端）

前置工具：[uv](https://docs.astral.sh/uv/)（Python 由 uv 托管，无需单独安装）。

```bash
cd server
uv sync                      # 安装依赖（生成 .venv 与 uv.lock）
cp ../deploy/.env.example .env   # 填入 SECRET_KEY / LLM_* 等配置

# 需要 PostgreSQL 16 + pgvector（可用 Docker 起一个）
uv run alembic upgrade head

uv run uvicorn app.main:app --reload          # API（/docs 开发默认开）
uv run python -m app.workers.runner           # worker（任务流水线）

uv run pytest -q          # 单元测试；集成测试需可用数据库，否则自动跳过
uv run ruff check . && uv run ruff format --check .
uv run mypy app
```

说明：

- worker 完整运行需要 embedding 依赖与模型：`uv sync --extra embed`（首次约 2.3GB 下载）；仅调试 API 可省略，embed 任务会以明确错误失败。
- JS 渲染兜底为可选：`uv sync --extra render` 并配置 `PLAYWRIGHT_CDP_URL`。
- 一键部署见 `deploy/`（`docker compose up -d`，api 启动时自动执行迁移）。

