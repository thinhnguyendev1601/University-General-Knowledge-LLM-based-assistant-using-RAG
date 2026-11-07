"""Cheap liveness and bounded dependency probes, without generating an answer."""
from functools import lru_cache
import json
import time
import urllib.request

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import QueuePool

from api.rag_runtime import STATE
from api.settings import ROOT, Settings, get_settings

router = APIRouter(prefix="/api/health", tags=["Operations"])


@lru_cache
def expected_revision():
    return ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_current_head()


@lru_cache
def get_probe_engine():
    url = get_settings().database_url
    # A separate, small pool prevents health probes from waiting behind app traffic.
    existing = make_url(url).query.get("options", "")
    if not isinstance(existing, str):
        existing = " ".join(existing)
    options = {"connect_timeout": 2, "options": existing + " -c statement_timeout=2000 -c lock_timeout=1000"} if url.startswith("postgresql") else {"check_same_thread": False}
    return create_engine(url, pool_size=1, max_overflow=0, pool_timeout=1,
                         poolclass=QueuePool, hide_parameters=True, connect_args=options)


def probe_database(engine):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        return "ready" if revision == [expected_revision()] else "migration_required"
    except Exception:
        return "unavailable"


_provider_cache = {}


def close_health_resources():
    if get_probe_engine.cache_info().currsize:
        get_probe_engine().dispose()
        get_probe_engine.cache_clear()
    _provider_cache.clear()


def probe_provider(pipe):
    provider = pipe.llm
    if provider is None:
        return "disabled"
    if not hasattr(provider, "url"):
        return "ready"  # In-process adapters used in tests; no network provider.
    key = (provider.url, provider.model)
    cached = _provider_cache.get(key)
    if cached and time.monotonic() - cached[0] < 5:
        return cached[1]
    try:
        with urllib.request.urlopen(provider.url.rstrip("/") + "/api/tags", timeout=2) as response:
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("Oversized provider response")
            models = {item["name"] for item in json.loads(raw).get("models", [])}
        model = provider.model if ":" in provider.model.rsplit("/", 1)[-1] else provider.model + ":latest"
        status = "ready" if model in models else "model_missing"
    except Exception:
        status = "unavailable"
    # Bound the tiny cache even if operators repeatedly change provider settings.
    if len(_provider_cache) >= 8:
        _provider_cache.clear()
    _provider_cache[key] = (time.monotonic(), status)
    return status


@router.get("/live")
def live():
    return {"status": "alive"}


@router.get("/ready")
def ready(settings: Settings = Depends(get_settings), engine=Depends(get_probe_engine)):
    components = {"database": probe_database(engine), "rag": "disabled", "model": "disabled"}
    if settings.rag_enabled:
        pipe = STATE.get("pipe")
        components["rag"] = "ready" if pipe is not None and len(pipe.index.chunks) > 0 else "not_loaded"
        components["model"] = probe_provider(pipe) if components["rag"] == "ready" else "not_checked"
    available = components["database"] == "ready" and all(
        components[key] in {"ready", "disabled"} for key in ("rag", "model"))
    return JSONResponse(status_code=200 if available else 503,
                        content={"status": "ready" if available else "not_ready", "components": components},
                        headers={"Cache-Control": "no-store"})
