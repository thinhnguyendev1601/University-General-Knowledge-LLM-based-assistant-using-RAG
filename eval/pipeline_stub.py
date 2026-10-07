"""Throw-away baseline pipelines so the harness can be smoke-tested TODAY.

    build_keyword_baseline : paragraph chunks + IDF-weighted term overlap + a refusal threshold
    build_oracle           : cheats by reading the test set; every retrieval metric must be 1.0
    build_always_refuse    : refusal recall must be 1.0, everything else 0

Replace with the real pipeline by changing `pipeline:` in the run config to
"your_pkg.module:build_fn". A build function returns any object with .answer(query) -> AnswerResult.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path

from core.schemas import AnswerResult, Chunk, Citation, ScoredChunk, make_chunk_id
from core.textnorm import normalize_text

_TOK = re.compile(r"\w+", re.UNICODE)


def tokenize(s: str) -> list[str]:
    return [t for t in _TOK.findall(normalize_text(s).casefold()) if len(t) > 1]


def paragraph_chunks(doc_id: str, text: str, min_chars: int = 200, max_chars: int = 1200) -> list[Chunk]:
    """Naive chunker: split on blank lines, merge short paragraphs, cap length."""
    spans, pos = [], 0
    for para in re.split(r"\n\n+", text):
        start = text.find(para, pos)
        if start < 0 or not para.strip():
            continue
        pos = start + len(para)
        spans.append([start, pos])
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and (merged[-1][1] - merged[-1][0] < min_chars) and (e - merged[-1][0] <= max_chars):
            merged[-1][1] = e
        else:
            merged.append([s, e])
    out = []
    for s, e in merged:
        for a in range(s, e, max_chars):
            b = min(a + max_chars, e)
            if b > a:
                out.append(
                    Chunk(chunk_id=make_chunk_id(doc_id, a, b), doc_id=doc_id, text=text[a:b], char_start=a, char_end=b,
                          chunker=f"stub-paragraph;max={max_chars}")
                )
    return out


class KeywordBaseline:
    def __init__(self, processed_dir: str = "data/processed", top_k: int = 5, refuse_below: float = 0.5, docs: list[str] | None = None):
        self.top_k, self.refuse_below = top_k, refuse_below
        self.chunks: list[Chunk] = []
        for p in sorted(Path(processed_dir).glob("*.txt")):
            if docs and p.stem not in docs:
                continue
            self.chunks += paragraph_chunks(p.stem, p.read_text(encoding="utf-8"))
        self.toks = [set(tokenize(c.text)) for c in self.chunks]
        df = Counter(t for ts in self.toks for t in ts)
        n = max(len(self.chunks), 1)
        self.idf = {t: math.log(1 + n / d) for t, d in df.items()}

    def retrieve(self, query: str) -> list[ScoredChunk]:
        q = set(tokenize(query))
        denom = sum(self.idf.get(t, math.log(1 + len(self.chunks))) for t in q) or 1.0
        scored = [(sum(self.idf.get(t, 0.0) for t in q & ts) / denom, i) for i, ts in enumerate(self.toks)]
        scored.sort(reverse=True)
        return [
            ScoredChunk(chunk=self.chunks[i], score=round(s, 4), rank=r, source="bm25")
            for r, (s, i) in enumerate(scored[: self.top_k], 1)
        ]

    def answer(self, query: str) -> AnswerResult:
        t0 = time.perf_counter()
        hits = self.retrieve(query)
        ms = (time.perf_counter() - t0) * 1000
        if not hits or hits[0].score < self.refuse_below:
            return AnswerResult(status="refused", answer="Không tìm thấy thông tin trong tài liệu. / Not found in the documents.",
                                refusal_reason="low_retrieval_score", retrieved=hits, latency_ms=ms,
                                trace={"top_score": hits[0].score if hits else None})
        top = hits[0].chunk
        first = re.split(r"(?<=[.!?])\s+", top.text.strip())[0][:300]
        return AnswerResult(status="answered", answer=top.text[:600], citations=[Citation(chunk_id=top.chunk_id, quote=first)],
                            retrieved=hits, latency_ms=ms, config_id="keyword-baseline")


def build_keyword_baseline(**kw) -> KeywordBaseline:
    return KeywordBaseline(**kw)


class _Oracle:
    def __init__(self, testset: str):
        self.by_q = {}
        for line in Path(testset).read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            self.by_q[d["question"]] = d

    def answer(self, query: str) -> AnswerResult:
        d = self.by_q[query]
        if not d["answerable"]:
            return AnswerResult(status="refused", answer="Not found.", refusal_reason="oracle")
        chunks, cites = [], []
        for r, ev in enumerate(d["evidence"], 1):
            c = Chunk(chunk_id=make_chunk_id(ev["doc_id"], ev["char_start"], ev["char_end"]), doc_id=ev["doc_id"],
                      text=ev["quote"], char_start=ev["char_start"], char_end=ev["char_end"])
            chunks.append(ScoredChunk(chunk=c, score=1.0, rank=r))
            cites.append(Citation(chunk_id=c.chunk_id, quote=ev["quote"]))
        return AnswerResult(status="answered", answer=d["gold_answer"], citations=cites, retrieved=chunks)


def build_oracle(testset: str = "eval/questions/testset.jsonl") -> _Oracle:
    return _Oracle(testset)


class _AlwaysRefuse:
    def answer(self, query: str) -> AnswerResult:
        return AnswerResult(status="refused", answer="Not found.", refusal_reason="always")


def build_always_refuse() -> _AlwaysRefuse:
    return _AlwaysRefuse()
