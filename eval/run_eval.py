"""Run one pipeline configuration over the test set and save everything needed to compare later.

    python -m eval.run_eval --config eval/config.example.yaml
    python -m eval.run_eval --config eval/config.example.yaml --final   # required to touch the TEST split

Outputs (eval/runs/<timestamp>_<run_name>/):
    config.yaml       exact config used (+ pipeline kwargs)
    meta.json         git commit, testset sha256, timestamp, counts
    results.jsonl     one record per question (answer, citations, retrieved ids/scores, per-question metrics)
    summary.json      overall + by category + by language
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import yaml

from core.schemas import AnswerResult, TestQuestion
from eval.metrics import citation_metrics, forbidden_hit, key_fact_recall, retrieval_metrics, summarize, summarize_by

ROOT = Path(__file__).resolve().parents[1]


def load_pipeline(spec: str, kwargs: dict):
    mod, _, attr = spec.partition(":")
    if not attr:
        raise SystemExit("pipeline must look like 'package.module:build_function'")
    return getattr(importlib.import_module(mod), attr)(**(kwargs or {}))


def load_testset(path: Path, split: str, min_status: str) -> list[TestQuestion]:
    order = {"draft": 0, "reviewed": 1, "approved": 2}
    qs = [TestQuestion.model_validate_json(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    qs = [q for q in qs if order[q.status] >= order[min_status]]
    return qs if split == "all" else [q for q in qs if q.split == split]


def evaluate_one(pipe, q: TestQuestion, ks, min_frac: float) -> dict:
    rec = {"id": q.id, "question": q.question, "lang": q.lang, "category": q.category, "answerable": q.answerable,
           "unanswerable_type": q.unanswerable_type, "split": q.split, "error": None}
    t0 = time.perf_counter()
    try:
        res: AnswerResult = pipe.answer(q.question)
    except Exception:  # a crash counts as a failed question, not a crashed run
        rec.update(refused=False, answer="", status="error", latency_ms=(time.perf_counter() - t0) * 1000,
                   error=traceback.format_exc(limit=3), metrics={}, citations=[], retrieved=[])
        return rec
    wall = (time.perf_counter() - t0) * 1000
    refused = res.status == "refused"
    m: dict = {}
    if q.answerable:
        m.update(retrieval_metrics(res.retrieved, q.evidence, ks, min_frac))
        kfr = key_fact_recall(q.key_facts, res.answer)
        m["key_fact_recall"] = kfr
        if q.forbidden_facts:
            m["forbidden_hit"] = forbidden_hit(q.forbidden_facts, res.answer)
        if not refused:
            m.update(citation_metrics(res, q.evidence, min_frac))
        m["auto_correct"] = (not refused) and kfr == 1.0 and not m.get("forbidden_hit", False)
    else:
        m["auto_correct"] = refused
    rec.update(
        status=res.status, refused=refused, answer=res.answer, refusal_reason=res.refusal_reason,
        latency_ms=res.latency_ms if res.latency_ms is not None else wall, metrics=m,
        citations=[c.model_dump() for c in res.citations],
        retrieved=[{"chunk_id": s.chunk.chunk_id, "rank": s.rank, "score": s.score} for s in sorted(res.retrieved, key=lambda s: s.rank)],
    )
    return rec


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT)
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
        return (out.stdout.strip() or "n/a") + ("+dirty" if dirty else "")
    except Exception:
        return "n/a"


def print_summary(s: dict) -> None:
    def f(x):
        return "  -  " if x is None else f"{x:.3f}"
    print(f"\n n={s['n']} (answerable {s['n_answerable']}, unanswerable {s['n_unanswerable']}, errors {s['n_errors']})")
    print(f" answer_accuracy_auto {f(s['answer_accuracy_auto'])} | abstention_acc {f(s['abstention_accuracy'])}")
    print(f" retrieval  hit@1 {f(s.get('hit@1'))}  hit@5 {f(s.get('hit@5'))}  recall@5 {f(s.get('evidence_recall@5'))}  MRR {f(s['mrr'])}")
    print(f" refusal    precision {f(s['refusal_precision'])}  recall {f(s['refusal_recall'])}  F1 {f(s['refusal_f1'])}")
    print(f"            false_refusal_rate {f(s['false_refusal_rate'])}  unsupported_answer_rate {f(s['unsupported_answer_rate'])}")
    print(f" citations  coverage {f(s['citation_coverage'])}  quote_verified {f(s['quote_verified_rate'])}  precision {f(s['citation_precision'])}")
    print(f" latency ms mean {f(s['latency_ms_mean'])}  p95 {f(s['latency_ms_p95'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--final", action="store_true", help="allow running on the frozen TEST split (logged)")
    ap.add_argument("--split", help="override split from config: dev | test | all")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    split = args.split or cfg.get("split", "dev")
    if split in {"test", "all"} and not args.final:
        raise SystemExit("Refusing to touch the TEST split without --final. Tune on dev; run test once per finished configuration.")

    ts_path = ROOT / cfg.get("testset", "eval/questions/testset.jsonl")
    qs = load_testset(ts_path, split, cfg.get("min_status", "draft"))
    if cfg.get("limit"):
        qs = qs[: int(cfg["limit"])]
    if not qs:
        raise SystemExit(f"no questions selected (split={split}); did you run `python -m eval.testset build`?")

    ks = cfg.get("k_values", [1, 3, 5, 10])
    min_frac = float(cfg.get("min_overlap_frac", 0.5))
    pipe = load_pipeline(cfg["pipeline"], cfg.get("pipeline_kwargs"))

    run_id = f"{datetime.now():%Y%m%d-%H%M%S}_{cfg.get('run_name', 'run')}"
    out_dir = ROOT / cfg.get("out_dir", "eval/runs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for i, q in enumerate(qs, 1):
        records.append(evaluate_one(pipe, q, ks, min_frac))
        if i % 10 == 0 or i == len(qs):
            print(f"  {i}/{len(qs)}", end="\r", flush=True)

    summary = {"overall": summarize(records, ks), "by_category": summarize_by(records, "category", ks), "by_lang": summarize_by(records, "lang", ks)}
    (out_dir / "results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    meta = {"run_id": run_id, "split": split, "n": len(qs), "git_commit": git_commit(), "testset_sha256": hashlib.sha256(ts_path.read_bytes()).hexdigest(),
            "python": sys.version.split()[0]}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if split in {"test", "all"}:
        with open(ROOT / cfg.get("out_dir", "eval/runs") / "test_runs.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{run_id}\t{meta['git_commit']}\tsplit={split}\n")

    print(f"\nrun: {run_id}  (split={split})")
    print_summary(summary["overall"])
    try:
        shown = out_dir.relative_to(ROOT)
    except ValueError:
        shown = out_dir
    print(f"\nsaved to {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
