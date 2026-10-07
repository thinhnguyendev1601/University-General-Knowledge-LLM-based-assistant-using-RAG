"""Pure metric functions (no I/O). Everything is span-based so it survives re-chunking.

A retrieved chunk "covers" an evidence span when they are in the same document and the
overlap is at least `min_frac` of the evidence span's length (default 0.5).
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Iterable, Optional

from core.schemas import AnswerResult, EvidenceSpan, ScoredChunk
from core.textnorm import match_form


# ------------------------------------------------------------------ span helpers
def overlap_len(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def covers(sc: ScoredChunk, ev: EvidenceSpan, min_frac: float = 0.5) -> bool:
    if ev.char_start is None or ev.char_end is None:
        raise ValueError(f"evidence for {ev.doc_id} has no resolved span; run `python -m eval.testset build`")
    c = sc.chunk
    if c.doc_id != ev.doc_id:
        return False
    need = max(1, ev.char_end - ev.char_start)
    return overlap_len(c.char_start, c.char_end, ev.char_start, ev.char_end) / need >= min_frac


# -------------------------------------------------------------------- retrieval
def retrieval_metrics(
    retrieved: list[ScoredChunk],
    evidence: list[EvidenceSpan],
    ks: Iterable[int] = (1, 3, 5, 10),
    min_frac: float = 0.5,
) -> dict[str, float]:
    """hit@k            : 1 if ANY evidence span is covered by a top-k chunk
       evidence_recall@k: fraction of evidence spans covered by top-k chunks
       rr               : reciprocal rank of the first chunk covering any evidence span"""
    ranked = sorted(retrieved, key=lambda s: s.rank)
    out: dict[str, float] = {}
    first_rank: Optional[int] = None
    for sc in ranked:
        if any(covers(sc, ev, min_frac) for ev in evidence):
            first_rank = sc.rank
            break
    out["rr"] = 1.0 / first_rank if first_rank else 0.0
    for k in ks:
        top = ranked[:k]
        covered = [any(covers(sc, ev, min_frac) for sc in top) for ev in evidence]
        out[f"hit@{k}"] = 1.0 if any(covered) else 0.0
        out[f"evidence_recall@{k}"] = sum(covered) / len(evidence) if evidence else 0.0
    return out


# ----------------------------------------------------------------------- answers
def fact_present(fact: str, answer: str) -> bool:
    """A fact may list alternatives separated by '|' (e.g. '2.0|2,0'). Case/space-insensitive,
    diacritic-SENSITIVE (Vietnamese diacritics change meaning)."""
    a = match_form(answer)
    return any(alt.strip() and match_form(alt) in a for alt in fact.split("|"))


def key_fact_recall(key_facts: list[str], answer: str) -> float:
    if not key_facts:
        return 1.0
    return sum(fact_present(f, answer) for f in key_facts) / len(key_facts)


def forbidden_hit(forbidden: list[str], answer: str) -> bool:
    return any(fact_present(f, answer) for f in forbidden)


# --------------------------------------------------------------------- citations
def citation_metrics(result: AnswerResult, evidence: list[EvidenceSpan], min_frac: float = 0.5) -> dict[str, float]:
    """quote_verified_rate: cited quote really appears in the cited chunk (anti-fabrication check)
       citation_precision : cited chunks that cover some evidence span
       citation_recall    : evidence spans covered by some cited chunk"""
    by_id = {sc.chunk.chunk_id: sc for sc in result.retrieved}
    cites = result.citations
    if not cites:
        return {"has_citation": 0.0, "quote_verified_rate": 0.0, "citation_precision": 0.0, "citation_recall": 0.0}
    verified, prec_hits = 0, 0
    cited_chunks: list[ScoredChunk] = []
    for c in cites:
        sc = by_id.get(c.chunk_id)
        if sc is None:
            continue  # cites something that was never retrieved => invalid
        cited_chunks.append(sc)
        if match_form(c.quote) and match_form(c.quote) in match_form(sc.chunk.text):
            verified += 1
        if evidence and any(covers(sc, ev, min_frac) for ev in evidence):
            prec_hits += 1
    rec = (
        sum(any(covers(sc, ev, min_frac) for sc in cited_chunks) for ev in evidence) / len(evidence)
        if evidence
        else 0.0
    )
    return {
        "has_citation": 1.0,
        "quote_verified_rate": verified / len(cites),
        "citation_precision": prec_hits / len(cites),
        "citation_recall": rec,
    }


# ------------------------------------------------------------------ aggregation
def _mean(xs: list[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def _pct(xs: list[float], q: float) -> Optional[float]:
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 1)


def summarize(records: list[dict], ks: Iterable[int] = (1, 3, 5, 10)) -> dict:
    """records: per-question dicts produced by run_eval (see run_eval.evaluate_one)."""
    ans = [r for r in records if r["answerable"]]
    una = [r for r in records if not r["answerable"]]
    ok = [r for r in records if not r.get("error")]

    tp = sum(1 for r in una if r["refused"])  # refused when it should
    fn = sum(1 for r in una if not r["refused"])  # answered an unanswerable question  => unsupported answer
    fp = sum(1 for r in ans if r["refused"])  # refused an answerable question        => false refusal
    tn = sum(1 for r in ans if not r["refused"])
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)

    m: dict = {
        "n": len(records),
        "n_answerable": len(ans),
        "n_unanswerable": len(una),
        "n_errors": len(records) - len(ok),
        "answer_accuracy_auto": _mean([1.0 if r["metrics"].get("auto_correct") else 0.0 for r in ans]),
        "abstention_accuracy": _mean([1.0 if r["refused"] == (not r["answerable"]) else 0.0 for r in records]),
        "refusal_precision": round(prec, 4) if prec is not None else None,
        "refusal_recall": round(rec, 4) if rec is not None else None,
        "refusal_f1": round(f1, 4) if f1 is not None else None,
        "false_refusal_rate": round(fp / len(ans), 4) if ans else None,
        "unsupported_answer_rate": round(fn / len(una), 4) if una else None,
        "confusion": {"TP_refused_correctly": tp, "FN_unsupported_answer": fn, "FP_false_refusal": fp, "TN_answered": tn},
    }
    with_ev = [r for r in ans if r["metrics"].get("rr") is not None]
    for k in ks:
        m[f"hit@{k}"] = _mean([r["metrics"][f"hit@{k}"] for r in with_ev])
        m[f"evidence_recall@{k}"] = _mean([r["metrics"][f"evidence_recall@{k}"] for r in with_ev])
    m["mrr"] = _mean([r["metrics"]["rr"] for r in with_ev])

    answered_ans = [r for r in ans if not r["refused"]]
    m["key_fact_recall_when_answered"] = _mean([r["metrics"]["key_fact_recall"] for r in answered_ans])
    vc = [r for r in answered_ans if r["metrics"].get("forbidden_hit") is not None]
    m["forbidden_fact_rate"] = _mean([1.0 if r["metrics"]["forbidden_hit"] else 0.0 for r in vc])

    answered = [r for r in records if not r["refused"] and not r.get("error")]
    cit = [r for r in answered if r["answerable"]]
    m["citation_coverage"] = _mean([r["metrics"].get("has_citation", 0.0) for r in cit])
    withc = [r for r in cit if r["metrics"].get("has_citation")]
    m["quote_verified_rate"] = _mean([r["metrics"]["quote_verified_rate"] for r in withc])
    m["citation_precision"] = _mean([r["metrics"]["citation_precision"] for r in withc])
    m["citation_recall"] = _mean([r["metrics"]["citation_recall"] for r in withc])

    lat = [r["latency_ms"] for r in records if r.get("latency_ms") is not None]
    m["latency_ms_mean"] = _mean(lat)
    m["latency_ms_p50"] = _pct(lat, 0.5)
    m["latency_ms_p95"] = _pct(lat, 0.95)
    return m


def summarize_by(records: list[dict], key: str, ks: Iterable[int] = (1, 3, 5, 10)) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        groups[str(r[key])].append(r)
    return {g: summarize(rs, ks) for g, rs in sorted(groups.items())}
