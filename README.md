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
