"""结构化 JSON 日志：request_id / user_id / job_id 经 contextvars 贯穿 api 与 worker。"""

from __future__ import annotations

import logging

import structlog


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # 降噪：uvicorn access 日志交给本模块统一格式即可
    logging.getLogger("uvicorn.access").handlers = []
