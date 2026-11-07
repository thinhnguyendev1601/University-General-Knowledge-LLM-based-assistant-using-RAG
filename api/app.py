"""Thin HTTP layer over rag.pipeline.answer() for the React chat UI.

    uvicorn api.app:app --port 8000          (run from the repo root)

Implements the frontend contract (projectsoftwareengineeringfrontend/CLAUDE.md §6):
    POST /api/chat/messages {conversationId, content, institutionId?} -> ChatMessage
plus GET /api/institutions (school picker) and GET /api/health.
Out of scope here (backend lead's lane): auth/JWT, Postgres, conversation storage - the UI
keeps conversations in localStorage for now (BACKEND_BLOCKED_FEATURES.md).

Config via env vars: RAG_LLM=ollama|none, RAG_LLM_MODEL=llama3.2, OLLAMA_URL, RAG_GATE=0.0
"""
from __future__ import annotations

import os
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.schemas import AnswerResult
from rag.pipeline import DensePipeline

STATE: dict = {}
_LOCK = threading.Lock()  # one CPU-bound LLM call at a time; parallel calls would just thrash


@asynccontextmanager
async def lifespan(app: FastAPI):
    # loads ~900 chunks + bge-m3 once (~20 s); embeddings come from data/index/ cache
    STATE["pipe"] = DensePipeline(
        llm=os.getenv("RAG_LLM", "ollama"),
        llm_model=os.getenv("RAG_LLM_MODEL", "llama3.2"),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
        gate=float(os.getenv("RAG_GATE", "0.0")),
    )
    yield
    STATE.clear()


app = FastAPI(title="University Knowledge Assistant API", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def _error(_, exc: HTTPException):
    # the UI's httpClient reads {message}
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


class SendMessage(BaseModel):
    conversationId: str
    content: str = Field(min_length=1, max_length=2000)
    institutionId: str | None = None  # from the school picker; None = detect from the question


def _citations(r: AnswerResult, pipe: DensePipeline) -> list[dict]:
    by_id = {s.chunk.chunk_id: s.chunk for s in r.retrieved}
    out = []
    for c in r.citations:
        ch = by_id.get(c.chunk_id)
        meta = pipe.meta.get(ch.doc_id) if ch else None
        out.append({"chunkId": c.chunk_id, "docId": ch.doc_id if ch else None,
                    "title": meta.title if meta else None, "sourceUrl": meta.source_url if meta else None,
                    "section": " > ".join(ch.section_path) if ch else "", "page": ch.page_start if ch else None,
                    "quote": c.quote})
    return out


def _content(r: AnswerResult, cites: list[dict]) -> str:
    """Plain-text answer + sources, so the current chat UI shows citations without changes."""
    if r.status == "refused" or not cites:
        return r.answer
    lines = [r.answer, "", "Nguồn / Sources:"]
    for i, c in enumerate(cites, 1):
        where = " — ".join(x for x in (c["title"], c["section"].split(" > ")[-1] if c["section"] else "",
                                         f"tr. {c['page']}" if c["page"] else "") if x)
        lines.append(f"[{i}] {where}\n    “{c['quote']}”")
    return "\n".join(lines)


@app.post("/api/chat/messages")
def send_message(body: SendMessage) -> dict:
    pipe: DensePipeline = STATE["pipe"]
    try:
        with _LOCK:
            r = pipe.answer(body.content, institution=body.institutionId)
    except ValueError as e:  # unknown institutionId
        raise HTTPException(400, str(e))
    except RuntimeError as e:  # Ollama down / model not pulled
        raise HTTPException(503, str(e))
    cites = _citations(r, pipe)
    inst = r.trace.get("institution") or {}
    return {
        # --- ChatMessage (frontend types/chat.ts) ---
        "id": str(uuid.uuid4()),
        "conversationId": body.conversationId,
        "role": "assistant",
        "content": _content(r, cites),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        # --- optional extras for a future citation panel ---
        "status": r.status,
        "answer": r.answer,
        "citations": cites,
        "refusalReason": r.refusal_reason,
        "institution": {"ids": inst.get("ids", []), "source": inst.get("source")},
        "latencyMs": round(r.latency_ms or 0),
    }


@app.get("/api/institutions")
def list_institutions() -> list[dict]:
    return STATE["pipe"].institution_options()


@app.get("/api/health")
def health() -> dict:
    p: DensePipeline = STATE["pipe"]
    return {"status": "ok", "chunks": len(p.index.chunks), "embedder": p.index.embedder.name,
            "llm": p.llm.name if p.llm else None, "config": p.config_id}
