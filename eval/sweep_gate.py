"""Offline sweep of a retrieval-score refusal gate (no LLM calls needed).

Run a DEV evaluation with the gate switched off (pipeline never refuses on score), then:

    python -m eval.sweep_gate eval/runs/<run_dir>

For each candidate threshold t the gate would refuse whenever the top retrieved score < t.
Prints false-refusal vs unsupported-answer trade-off so you can pick t from data.
Only meaningful when the score scale is stable (e.g. reranker score or cosine), and only
on DEV questions. Never pick a threshold on the test split.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def sweep(records: list[dict], n_points: int = 15) -> list[dict]:
    tops = []
    for r in records:
        if r.get("error"):
            continue
        s = r["retrieved"][0]["score"] if r.get("retrieved") else float("-inf")
        tops.append((s, r["answerable"], r.get("metrics", {}).get("key_fact_recall", 0.0), r.get("metrics", {}).get("hit@5", 0.0)))
    if not tops:
        return []
    scores = sorted({s for s, *_ in tops if s != float("-inf")})
    if not scores:
        return []
    step = max(1, len(scores) // n_points)
    cands = [scores[0] - 1e-4] + scores[::step] + [scores[-1] + 1e-4]
    ans = [t for t in tops if t[1]]
    una = [t for t in tops if not t[1]]
    rows = []
    for t in sorted({round(c, 4) for c in cands}):
        false_ref = sum(1 for s, *_ in ans if s < t) / max(len(ans), 1)
        unsupported = sum(1 for s, *_ in una if s >= t) / max(len(una), 1)
        # "would still answer correctly": answered and retrieval found the evidence
        answered_ok = sum(1 for s, _, kf, h in ans if s >= t and h == 1.0) / max(len(ans), 1)
        rows.append({"threshold": t, "false_refusal_rate": round(false_ref, 3),
                     "unsupported_answer_rate": round(unsupported, 3), "answerable_kept_with_evidence": round(answered_ok, 3),
                     "balanced_error": round((false_ref + unsupported) / 2, 3)})
    return rows


def main(run_dir: str) -> None:
    recs = [json.loads(l) for l in (Path(run_dir) / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = sweep(recs)
    if not rows:
        raise SystemExit("no usable records")
    print(f"{'threshold':>10} {'false_refusal':>14} {'unsupported':>12} {'kept+evidence':>14} {'balanced_err':>13}")
    for r in rows:
        print(f"{r['threshold']:>10} {r['false_refusal_rate']:>14} {r['unsupported_answer_rate']:>12} {r['answerable_kept_with_evidence']:>14} {r['balanced_error']:>13}")
    best = min(rows, key=lambda r: (r["balanced_error"], r["threshold"]))
    print(f"\nlowest balanced error at threshold {best['threshold']} (pick with your own risk preference: for a university assistant, unsupported answers usually cost more than refusals)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
