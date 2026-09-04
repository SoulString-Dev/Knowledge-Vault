"""FastAPI 装配：中间件、错误处理、路由注册、健康检查。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import admin, articles, auth, search, tags
from app.config import get_settings
from app.core.errors import AppError
from app.db import dispose_engine, get_engine
from app.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="Knowledge Vault",
        version="0.1.0",
        lifespan=lifespan,
        # 生产默认关闭 /docs 与 /openapi.json（ENABLE_DOCS 开关）
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    @app.middleware("http")
    async def bind_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        structlog.contextvars.clear_contextvars()
        request_id = uuid.uuid4().hex[:12]
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"code": exc.code, "message": exc.message, "details": exc.details or {}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()[:10]
        ]
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "参数校验失败",
                "details": {"errors": errors},
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        structlog.get_logger().exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL", "message": "服务器内部错误", "details": {}},
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(status_code=503, content={"status": "db unavailable"})
        return JSONResponse(content={"status": "ok"})

    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(articles.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(tags.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    return app


app = create_app()
