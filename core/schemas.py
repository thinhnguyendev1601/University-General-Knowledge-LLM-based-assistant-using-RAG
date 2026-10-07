"""Shared data contracts for the University Knowledge Assistant.

Three groups:
  1. Corpus      : DocumentMeta (one manifest row) and Chunk (unit of retrieval)
  2. Pipeline    : ScoredChunk, Citation, AnswerResult, RAGPipeline (what eval calls)
  3. Evaluation  : EvidenceSpan, TestQuestion

Invariant that everything else relies on:
    chunk.text == canonical_text(chunk.doc_id)[chunk.char_start : chunk.char_end]
where canonical_text = data/processed/<doc_id>.txt (output of scripts/extract_text.py).
"""
from __future__ import annotations

from typing import Literal, Optional, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

Lang = Literal["vi", "en", "mixed"]
QLang = Literal["vi", "en"]

DocRole = Literal["indexed", "holdout", "excluded"]
DocStatus = Literal["current", "superseded", "unknown"]
ProvenanceTier = Literal["A", "B", "C"]  # A official primary, B official mirror, C third party

ChunkType = Literal["paragraph", "list", "table", "heading", "other"]

Category = Literal[
    "single_fact",
    "procedure",
    "multi_section",
    "multi_doc",
    "table_numeric",
    "cross_lingual",
    "version_conflict",
    "unanswerable",
    "adversarial",
]
UnanswerableType = Literal[
    "out_of_domain",      # nothing to do with the university
    "absent_in_domain",   # plausible, but no indexed document answers it
    "false_premise",      # question presupposes something the documents don't support
    "holdout_only",       # answer exists only in a document excluded from the index
    "prompt_injection",   # tries to make the system ignore the documents
]
Difficulty = Literal["easy", "medium", "hard"]
ReviewStatus = Literal["draft", "reviewed", "approved"]
Split = Literal["dev", "test"]


# --------------------------------------------------------------------------- corpus
class DocumentMeta(BaseModel):
    """One row of data/manifest.csv (see docs/01_corpus_v0_guide.md for field meaning)."""

    doc_id: str = Field(pattern=r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$")
    title: str
    publisher: str
    doc_type: str  # regulation | handbook | faq | procedure | circular | other
    lang: Lang
    doc_version: str = "1"
    publication_date: Optional[str] = None  # ISO date or year
    effective_date: Optional[str] = None
    source_url: Optional[str] = None
    landing_url: Optional[str] = None
    retrieved_on: Optional[str] = None
    file_format: Optional[str] = None  # pdf | docx | html
    n_pages: Optional[int] = None
    has_text_layer: Optional[Literal["yes", "no", "partial"]] = None
    has_tables: Optional[Literal["yes", "no"]] = None
    provenance_tier: ProvenanceTier = "A"
    license_note: str = ""
    role: DocRole = "indexed"
    version_group: Optional[str] = None  # same document family across years
    doc_status: DocStatus = "unknown"
    status_checked_on: Optional[str] = None
    sha256_raw: Optional[str] = None
    sha256_text: Optional[str] = None
    owner: Optional[str] = None
    notes: str = ""


class Chunk(BaseModel):
    chunk_id: str  # f"{doc_id}:{char_start}:{char_end}"  (deterministic)
    doc_id: str
    doc_version: str = "1"
    text: str  # == canonical_text[char_start:char_end]
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    page_start: Optional[int] = None  # 1-based; None for DOCX/HTML
    page_end: Optional[int] = None
    section_path: list[str] = Field(default_factory=list)  # ["Chương II", "Điều 8. ..."]
    lang: Lang = "en"
    chunk_type: ChunkType = "paragraph"
    token_count: Optional[int] = None
    chunker: str = ""  # e.g. "struct-v1;max=450;overlap=50"  (which recipe produced it)

    @model_validator(mode="after")
    def _check_span(self) -> "Chunk":
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be > char_start")
        if self.chunk_id != make_chunk_id(self.doc_id, self.char_start, self.char_end):
            raise ValueError("chunk_id must equal make_chunk_id(doc_id, char_start, char_end)")
        return self

    def embedding_text(self) -> str:
        """Text that goes into the embedder: heading path + body (contextual header)."""
        header = " > ".join(self.section_path)
        return f"{header}\n{self.text}" if header else self.text


def make_chunk_id(doc_id: str, char_start: int, char_end: int) -> str:
    return f"{doc_id}:{char_start}:{char_end}"


def verify_chunk(chunk: "Chunk", canonical_text: str) -> None:
    """Call in the ingestion tests for EVERY chunk. Raises AssertionError if the invariant is broken."""
    assert canonical_text[chunk.char_start : chunk.char_end] == chunk.text, f"offset/text mismatch in {chunk.chunk_id}"


# ------------------------------------------------------------------------ pipeline
class ScoredChunk(BaseModel):
    chunk: Chunk
    score: float
    rank: int = Field(ge=1)  # 1 = best, after the final retrieval/rerank stage
    source: Literal["dense", "bm25", "hybrid", "rerank"] = "hybrid"


class Citation(BaseModel):
    chunk_id: str
    quote: str  # verbatim span the answer relies on; must be a substring of that chunk


class AnswerResult(BaseModel):
    status: Literal["answered", "refused"]
    answer: str = ""  # for "refused": a short user-facing message
    citations: list[Citation] = Field(default_factory=list)
    refusal_reason: Optional[str] = None  # e.g. "low_retrieval_score" | "model_abstained" | "unverified_citation"
    retrieved: list[ScoredChunk] = Field(default_factory=list)  # what the generator actually saw, ranked
    language: Optional[QLang] = None
    latency_ms: Optional[float] = None
    config_id: Optional[str] = None
    trace: dict = Field(default_factory=dict)  # free-form debug info (scores, gate values, judge output)


class RAGPipeline(Protocol):
    def answer(self, query: str) -> AnswerResult: ...


# ---------------------------------------------------------------------- evaluation
class EvidenceSpan(BaseModel):
    doc_id: str
    quote: str  # verbatim from data/processed/<doc_id>.txt (whitespace-insensitive)
    page: Optional[int] = None  # informational only
    char_start: Optional[int] = None  # filled by `eval.testset build`
    char_end: Optional[int] = None


class TestQuestion(BaseModel):
    __test__ = False  # stop pytest trying to collect this class

    id: str = Field(pattern=r"^[A-Z]{2,3}-\d{3}$")  # author code + running number, e.g. TM-014
    question: str
    lang: QLang
    category: Category
    answerable: bool
    unanswerable_type: Optional[UnanswerableType] = None
    gold_answer: str = ""
    key_facts: list[str] = Field(default_factory=list)  # each may hold alternatives split by "|"
    forbidden_facts: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    difficulty: Difficulty = "medium"
    tags: list[str] = Field(default_factory=list)  # no_diacritics, informal, typo, abbreviation, ...
    split: Optional[Split] = None  # assigned by tooling, never by hand
    author: str = ""
    reviewer: str = ""
    status: ReviewStatus = "draft"
    notes: str = ""

    @field_validator("question")
    @classmethod
    def _q_nonempty(cls, v: str) -> str:
        if len(v.strip()) < 8:
            raise ValueError("question too short")
        return v.strip()
