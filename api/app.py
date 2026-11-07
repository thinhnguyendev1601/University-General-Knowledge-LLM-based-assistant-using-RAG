"""Thin HTTP layer over rag.pipeline.answer() for the React chat UI.

    uvicorn api.app:app --port 8000          (run from the repo root)

Implements the frontend contract (projectsoftwareengineeringfrontend/CLAUDE.md §6):
    POST /api/chat/messages {conversationId, content, institutionId?} -> ChatMessage
plus GET /api/institutions (school picker) and GET /api/health.
Cookie authentication and PostgreSQL accounts are provided by api.auth.
Private conversation persistence is provided by api.chat and connected to the main frontend.

Config via env vars: RAG_LLM=ollama|none, RAG_LLM_MODEL=llama3.2, OLLAMA_URL, RAG_GATE=0.0
"""
from __future__ import annotations

import os
import time
from uuid import UUID, uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api.auth import router as auth_router
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.mail import MailDeliveryError
from api.settings import get_settings
from api.rag_runtime import STATE, get_pipeline
from rag.pipeline import DensePipeline
from api.rag_admission import shutdown_admission
from api.health import router as health_router, close_health_resources
from api.telemetry import emit, http_request_id, install_access_filter

install_access_filter()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # loads ~900 chunks + bge-m3 once (~20 s); embeddings come from data/index/ cache
    if get_settings().rag_enabled:
        STATE["pipe"] = DensePipeline(
            llm=os.getenv("RAG_LLM", "ollama"),
            llm_model=os.getenv("RAG_LLM_MODEL", "llama3.2"),
            ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            gate=float(os.getenv("RAG_GATE", "0.0")),
        )
    try:
        yield
    finally:
        shutdown_admission()
        close_health_resources()
        STATE.clear()


app = FastAPI(title="University Knowledge Assistant API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(health_router)


@app.middleware("http")
async def auth_privacy_headers(request: Request, call_next):
    incoming = request.headers.get("x-request-id", "")
    try:
        request_id = str(UUID(incoming)) if len(incoming) <= 36 else str(uuid4())
    except ValueError:
        request_id = str(uuid4())
    token = http_request_id.set(request_id)
    started = time.monotonic()
    status, error_type = 500, None
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-Id"] = request_id
        if request.url.path.startswith(("/api/auth", "/api/chat", "/api/admin", "/api/health")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response
    except Exception as error:
        error_type = type(error).__name__
        raise
    finally:
        route = request.scope.get("route")
        emit("http_request", method=request.method, route=getattr(route, "path", "unmatched"),
             status=status, elapsedMs=round((time.monotonic() - started) * 1000, 2), errorType=error_type)
        http_request_id.reset(token)


@app.exception_handler(HTTPException)
async def _error(_, exc: HTTPException):
    # the UI's httpClient reads {message}
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(_, exc: RequestValidationError):
    # Never echo raw validation input: it can contain passwords or account tokens.
    errors = [{"field": ".".join(str(item) for item in error["loc"][1:]), "message": error["msg"]}
              for error in exc.errors()]
    return JSONResponse(status_code=422, content={"message": "Dữ liệu không hợp lệ", "errors": errors})


@app.exception_handler(MailDeliveryError)
async def mail_unavailable(_, exc: MailDeliveryError):
    emit("dependency_failure", component="smtp", errorType=type(exc).__name__)
    return JSONResponse(status_code=503, content={"message": "Chưa gửi được email. Vui lòng thử lại sau."})


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(_, exc: SQLAlchemyError):
    emit("dependency_failure", component="database", errorType=type(exc).__name__)
    return JSONResponse(status_code=503, content={"message": "Dịch vụ dữ liệu tạm thời không khả dụng."})


@app.get("/api/institutions")
def list_institutions() -> list[dict]:
    return get_pipeline().institution_options()


@app.get("/api/health")
def health() -> dict:
    if not get_settings().rag_enabled:
        return {"status": "ok", "rag": "disabled"}
    p = get_pipeline()
    return {"status": "ok", "chunks": len(p.index.chunks), "embedder": p.index.embedder.name,
            "llm": p.llm.name if p.llm else None, "config": p.config_id}
