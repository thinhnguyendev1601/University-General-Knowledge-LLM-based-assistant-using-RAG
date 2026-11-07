"""Live check against the real stack (bge-m3 + Ollama). Skipped unless Ollama is running and
data/processed/ exists, so `pytest` stays fast and offline. Run it on purpose with:

    RAG_LIVE=1 pytest tests/test_live_llm.py -q        (~1-2 min on CPU)

Asserts behaviour, not exact wording: a 3B model's phrasing changes between runs/models.
"""
import json
import os
import urllib.request
from pathlib import Path

import pytest

MODEL = os.getenv("RAG_LLM_MODEL", "llama3.2")


def _ollama_has_model() -> bool:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            return any(m["name"].split(":")[0] == MODEL.split(":")[0] for m in json.loads(r.read())["models"])
    except OSError:
        return False


pytestmark = pytest.mark.skipif(
    not (os.getenv("RAG_LIVE") and Path("data/processed").is_dir() and _ollama_has_model()),
    reason="live test: set RAG_LIVE=1, run `ollama serve`, and have data/processed/ locally")


@pytest.fixture(scope="module")
def pipe():
    from rag.pipeline import DensePipeline
    return DensePipeline(llm="ollama", llm_model=MODEL)


def test_answers_with_a_verified_quote(pipe):
    r = pipe.answer("How long does the summer semester last?", institution="iu")
    assert r.status == "answered" and "7" in r.answer
    chunks = {s.chunk.chunk_id: s.chunk.text for s in r.retrieved}
    assert all(c.quote in chunks[c.chunk_id] for c in r.citations)  # every quote is verbatim


def test_vietnamese_question_detects_the_school(pipe):
    r = pipe.answer("Ở UIT khi nào sinh viên bị cảnh báo học tập?")
    assert r.trace["institution"]["ids"] == ["uit"]
    assert {s.chunk.doc_id for s in r.retrieved} <= {"uit-acad-reg-2022"}


def test_out_of_domain_is_refused(pipe):
    assert pipe.answer("What's the exchange rate between VND and USD today?").status == "refused"


def test_school_without_documents_is_refused_without_the_llm(pipe):
    assert pipe.answer("What is the tuition fee at MIT?").refusal_reason == "institution_not_covered"
