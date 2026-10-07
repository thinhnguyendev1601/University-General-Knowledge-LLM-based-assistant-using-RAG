"""Side-by-side comparison of runs -> markdown table (paste into the report / README).

    python -m eval.compare eval/runs/<runA> eval/runs/<runB> ...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

COLS = [
    ("answer_accuracy_auto", "acc(auto)"), ("hit@5", "hit@5"), ("evidence_recall@5", "recall@5"), ("mrr", "MRR"),
    ("refusal_precision", "ref.P"), ("refusal_recall", "ref.R"), ("false_refusal_rate", "false-ref"),
    ("unsupported_answer_rate", "unsupp."), ("quote_verified_rate", "quote✓"), ("latency_ms_p95", "p95 ms"),
]


def main(paths: list[str]) -> None:
    rows = []
    for p in paths:
        d = Path(p)
        s = json.loads((d / "summary.json").read_text(encoding="utf-8"))["overall"]
        m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        rows.append((d.name.split("_", 1)[-1], m["split"], s))
    print("| run | split | n | " + " | ".join(h for _, h in COLS) + " |")
    print("|---|---|---|" + "---|" * len(COLS))
    for name, split, s in rows:
        cells = ["-" if s.get(k) is None else f"{s[k]:.3f}" if isinstance(s[k], float) and s[k] <= 1.5 else str(s[k]) for k, _ in COLS]
        print(f"| {name} | {split} | {s['n']} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
