"""Test-set tooling: annotation CSV  ->  validated, span-resolved, split JSONL.

    python -m eval.testset build --csv eval/questions/annotations.csv --out eval/questions/testset.jsonl
    python -m eval.testset grep "canh cao hoc vu" --accent-insensitive     # absence / presence check

Design rules
  * The annotator's QUOTE is the source of truth; char offsets are derived and re-derived
    on every build, so changing the chunker never invalidates the test set.
  * Splits (dev/test) are assigned here, never by hand. They are sticky: once a question
    has a split in the output file it keeps it, so adding questions never shuffles old ones.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from core.schemas import DocumentMeta, EvidenceSpan, TestQuestion
from core.textnorm import collapse_ws, normalize_text

ROOT = Path(__file__).resolve().parents[1]
STATUS_ORDER = {"draft": 0, "reviewed": 1, "approved": 2}

# Target composition for the frozen ~100-question set (see docs/03_annotation_guide.md)
TARGETS = {
    "single_fact": 20, "procedure": 13, "multi_section": 8, "multi_doc": 4, "table_numeric": 10,
    "cross_lingual": 10, "version_conflict": 5, "unanswerable": 25, "adversarial": 5,
}

CSV_EVIDENCE_SLOTS = 3


# ------------------------------------------------------------------ quote resolution
def _collapse_with_map(text: str) -> tuple[str, list[int]]:
    out, idx, prev_space = [], [], False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space and out:
                out.append(" ")
                idx.append(i)
            prev_space = True
        else:
            out.append(ch)
            idx.append(i)
            prev_space = False
    return "".join(out), idx


class DocText:
    def __init__(self, text: str):
        self.text = text
        self.collapsed, self.idx = _collapse_with_map(text)

    def resolve(self, quote: str) -> tuple[Optional[tuple[int, int]], str]:
        """returns ((start, end) in canonical text | None, note). note in {'exact','multiple','fuzzy:<score>','not_found'}"""
        q = collapse_ws(normalize_text(quote))
        if not q:
            return None, "empty"
        pos = self.collapsed.find(q)
        if pos >= 0:
            note = "exact" if self.collapsed.find(q, pos + 1) < 0 else "multiple"
            return (self.idx[pos], self.idx[pos + len(q) - 1] + 1), note
        try:
            from rapidfuzz import fuzz

            al = fuzz.partial_ratio_alignment(q, self.collapsed, score_cutoff=90)
        except ImportError:
            al = None
        if al is not None:
            s, e = al.dest_start, max(al.dest_end - 1, al.dest_start)
            return (self.idx[s], self.idx[e] + 1), f"fuzzy:{al.score:.0f}"
        return None, "not_found"


def load_doc_texts(processed: Path) -> dict[str, DocText]:
    return {p.stem: DocText(p.read_text(encoding="utf-8")) for p in processed.glob("*.txt")}


def load_manifest(path: Path) -> dict[str, DocumentMeta]:
    out: dict[str, DocumentMeta] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for lineno, row in enumerate(csv.DictReader(f), start=2):
            row = {k: v.strip() for k, v in row.items() if k in DocumentMeta.model_fields and v and v.strip()}
            if not row.get("doc_id"):
                continue
            row.setdefault("title", "")
            row.setdefault("publisher", "")
            row.setdefault("doc_type", "other")
            if "n_pages" in row:
                row["n_pages"] = int(row["n_pages"])
            try:
                m = DocumentMeta(**row)
            except ValidationError as e:
                raise SystemExit(f"manifest row {lineno} ({row.get('doc_id')}): {e}")
            out[m.doc_id] = m
    return out


# ------------------------------------------------------------------------ CSV parsing
def _split_list(s: str, sep: str) -> list[str]:
    return [x.strip() for x in (s or "").split(sep) if x.strip()]


def _bool(s: str) -> bool:
    v = (s or "").strip().lower()
    if v in {"true", "yes", "y", "1"}:
        return True
    if v in {"false", "no", "n", "0"}:
        return False
    raise ValueError(f"answerable must be TRUE/FALSE, got {s!r}")


def row_to_question(row: dict) -> TestQuestion:
    ev = []
    for i in range(1, CSV_EVIDENCE_SLOTS + 1):
        doc, quote = (row.get(f"ev{i}_doc_id") or "").strip(), (row.get(f"ev{i}_quote") or "").strip()
        if doc or quote:
            page = (row.get(f"ev{i}_page") or "").strip()
            ev.append(EvidenceSpan(doc_id=doc, quote=quote, page=int(page) if page.isdigit() else None))
    return TestQuestion(
        id=(row.get("id") or "").strip(),
        question=row.get("question") or "",
        lang=(row.get("lang") or "").strip().lower(),
        category=(row.get("category") or "").strip(),
        answerable=_bool(row.get("answerable") or ""),
        unanswerable_type=(row.get("unanswerable_type") or "").strip() or None,
        gold_answer=(row.get("gold_answer") or "").strip(),
        key_facts=_split_list(row.get("key_facts") or "", "||"),
        forbidden_facts=_split_list(row.get("forbidden_facts") or "", "||"),
        evidence=ev,
        difficulty=(row.get("difficulty") or "medium").strip().lower(),
        tags=[t.strip() for t in (row.get("tags") or "").replace(",", ";").split(";") if t.strip()],
        author=(row.get("author") or "").strip(),
        reviewer=(row.get("reviewer") or "").strip(),
        status=(row.get("status") or "draft").strip().lower(),
        notes=(row.get("notes") or "").strip(),
    )


# ------------------------------------------------------------------------ validation
def validate(q: TestQuestion, docs: dict[str, DocText], manifest: dict[str, DocumentMeta]) -> tuple[list[str], list[str]]:
    errs, warns = [], []
    if q.category in {"unanswerable", "adversarial"}:
        if q.answerable:
            errs.append("category unanswerable/adversarial requires answerable=FALSE")
        if not q.unanswerable_type:
            errs.append("unanswerable_type required")
        if q.category == "adversarial" and q.unanswerable_type != "prompt_injection":
            errs.append("adversarial questions must use unanswerable_type=prompt_injection")
    else:
        if not q.answerable:
            errs.append("answerable=FALSE only allowed for categories unanswerable/adversarial")
        if q.unanswerable_type:
            errs.append("unanswerable_type must be empty for answerable questions")
    if q.answerable:
        if not q.gold_answer:
            errs.append("gold_answer required")
        if not q.key_facts:
            warns.append("no key_facts (auto-scoring will be weak)")
        if not q.evidence:
            errs.append("at least one evidence span required")
        if q.category in {"multi_section", "multi_doc"} and len(q.evidence) < 2:
            errs.append("multi_* categories need >= 2 evidence spans")
        if q.category == "multi_doc" and len({e.doc_id for e in q.evidence}) < 2:
            errs.append("multi_doc needs evidence from >= 2 different documents")
        if q.category == "version_conflict" and not q.forbidden_facts:
            errs.append("version_conflict needs forbidden_facts (the stale value)")
        for kf in q.key_facts:
            if not any(collapse_ws(a).casefold() in collapse_ws(q.gold_answer).casefold() for a in kf.split("|") if a.strip()):
                warns.append(f"key_fact {kf!r} not found in gold_answer")
    else:
        if q.key_facts:
            warns.append("key_facts ignored for unanswerable questions")
    for i, ev in enumerate(q.evidence, 1):
        meta = manifest.get(ev.doc_id)
        if meta is None:
            errs.append(f"evidence {i}: doc_id {ev.doc_id!r} not in manifest")
            continue
        if q.answerable and meta.role != "indexed":
            errs.append(f"evidence {i}: {ev.doc_id} has role={meta.role}; answerable questions must cite indexed docs")
        if q.unanswerable_type == "holdout_only" and meta.role != "holdout":
            errs.append(f"evidence {i}: holdout_only questions must cite a role=holdout doc")
        if len(ev.quote) > 600:
            warns.append(f"evidence {i}: quote is long ({len(ev.quote)} chars) - use the minimal sufficient span")
        dt = docs.get(ev.doc_id)
        if dt is None:
            errs.append(f"evidence {i}: no processed text for {ev.doc_id} (run scripts/extract_text.py)")
            continue
        span, note = dt.resolve(ev.quote)
        if span is None:
            errs.append(f"evidence {i}: quote not found in {ev.doc_id} ({note})")
        else:
            ev.char_start, ev.char_end = span
            if note == "multiple":
                warns.append(f"evidence {i}: quote occurs more than once in {ev.doc_id}; lengthen it")
            elif note.startswith("fuzzy"):
                warns.append(f"evidence {i}: quote matched only fuzzily ({note}); copy it from data/processed/{ev.doc_id}.txt")
    if q.category == "cross_lingual" and q.evidence:
        dl = {manifest[e.doc_id].lang for e in q.evidence if e.doc_id in manifest}
        if q.lang in dl and len(dl) == 1:
            warns.append("cross_lingual: question language equals evidence document language")
    if q.category == "adversarial" and not any(w in q.question.lower() for w in ("ignore", "bỏ qua", "bo qua", "forget", "quên", "your own knowledge", "kiến thức của bạn")):
        warns.append("adversarial question has no obvious injection phrase")
    return errs, warns


# ---------------------------------------------------------------------------- splits
def _h(seed: int, qid: str) -> int:
    return int(hashlib.sha256(f"{seed}:{qid}".encode()).hexdigest()[:8], 16)


def assign_splits(qs: list[TestQuestion], existing: dict[str, str], dev_frac: float, seed: int) -> None:
    """Sticky + stratified by category: keep old assignments, place each NEW question in the split that
    brings its category closest to dev_frac. Deterministic for a given (seed, set of ids)."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"dev": 0, "test": 0})
    for q in qs:
        if q.id in existing:
            q.split = existing[q.id]  # type: ignore[assignment]
            counts[q.category][q.split] += 1
    for q in sorted((q for q in qs if q.id not in existing), key=lambda q: _h(seed, q.id)):
        c = counts[q.category]
        total = c["dev"] + c["test"] + 1
        d_dev, d_test = abs((c["dev"] + 1) / total - dev_frac), abs(c["dev"] / total - dev_frac)
        if abs(d_dev - d_test) < 1e-9:
            q.split = "dev" if _h(seed, q.id) % 100 < dev_frac * 100 else "test"
        else:
            q.split = "dev" if d_dev < d_test else "test"
        c[q.split] += 1  # type: ignore[index]


# --------------------------------------------------------------------------- commands
def cmd_build(a: argparse.Namespace) -> int:
    docs = load_doc_texts(Path(a.processed))
    manifest = load_manifest(Path(a.manifest))
    out = Path(a.out)
    existing = {}
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                if d.get("split"):
                    existing[d["id"]] = d["split"]

    qs, n_err, n_warn, seen_ids, seen_q = [], 0, 0, set(), {}
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        for lineno, row in enumerate(csv.DictReader(f), start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            label = f"row {lineno} [{(row.get('id') or '?').strip()}]"
            try:
                q = row_to_question(row)
            except (ValidationError, ValueError) as e:
                msg = str(e).replace("\n", " ")[:300]
                print(f"ERROR {label}: {msg}")
                n_err += 1
                continue
            if STATUS_ORDER[q.status] < STATUS_ORDER[a.min_status]:
                continue
            errs, warns = validate(q, docs, manifest)
            if q.id in seen_ids:
                errs.append("duplicate id")
            seen_ids.add(q.id)
            nq = collapse_ws(q.question).casefold()
            if nq in seen_q:
                errs.append(f"duplicate question text (same as {seen_q[nq]})")
            seen_q[nq] = q.id
            if q.status != "draft" and (not q.reviewer or q.reviewer == q.author):
                errs.append("reviewed/approved questions need a reviewer different from the author")
            for e in errs:
                print(f"ERROR {label}: {e}")
            for w in warns:
                print(f"warn  {label}: {w}")
            n_err += len(errs)
            n_warn += len(warns)
            qs.append(q)

    print(f"\n{len(qs)} questions read, {n_err} errors, {n_warn} warnings")
    if n_err:
        print("Nothing written (fix errors first).")
        return 1
    assign_splits(qs, existing, a.dev_frac, a.seed)
    qs.sort(key=lambda q: q.id)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for q in qs:
            f.write(q.model_dump_json() + "\n")
    print(f"wrote {out}")
    report(qs)
    return 0


def report(qs: list[TestQuestion]) -> None:
    print(f"\n{'category':18} {'have':>4} {'target':>6}  vi/en   dev/test")
    for cat, tgt in TARGETS.items():
        sub = [q for q in qs if q.category == cat]
        lang = Counter(q.lang for q in sub)
        sp = Counter(q.split for q in sub)
        print(f"{cat:18} {len(sub):>4} {tgt:>6}  {lang['vi']:>2}/{lang['en']:<2}   {sp['dev']:>3}/{sp['test']:<3}")
    n_una = sum(1 for q in qs if not q.answerable)
    print(f"{'TOTAL':18} {len(qs):>4} {sum(TARGETS.values()):>6}   unanswerable share: {n_una / max(len(qs), 1):.0%}  (target ~30%)")
    print(f"by author: {dict(Counter(q.author for q in qs))}")


def _fold(s: str) -> str:
    out = []
    for c in s:
        b = unicodedata.normalize("NFD", c)[0]
        out.append("d" if b in "đĐ" else b)
    return "".join(out).casefold()


def cmd_grep(a: argparse.Namespace) -> int:
    proc = Path(a.processed)
    needle = collapse_ws(a.pattern)
    needle = _fold(needle) if a.accent_insensitive else needle.casefold()
    hits = 0
    for p in sorted(proc.glob("*.txt")):
        dt = DocText(p.read_text(encoding="utf-8"))
        hay = _fold(dt.collapsed) if a.accent_insensitive else dt.collapsed.casefold()
        start = 0
        while (i := hay.find(needle, start)) >= 0 and hits < a.max:
            lo, hi = max(0, i - 80), min(len(hay), i + len(needle) + 80)
            print(f"{p.stem} @{dt.idx[i]}: ...{dt.collapsed[lo:hi]}...")
            hits += 1
            start = i + len(needle)
    print(f"{hits} hit(s)" + (" (capped)" if hits >= a.max else ""))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m eval.testset")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--csv", default=str(ROOT / "eval/questions/annotations.csv"))
    b.add_argument("--out", default=str(ROOT / "eval/questions/testset.jsonl"))
    b.add_argument("--manifest", default=str(ROOT / "data/manifest.csv"))
    b.add_argument("--processed", default=str(ROOT / "data/processed"))
    b.add_argument("--min-status", default="draft", choices=list(STATUS_ORDER))
    b.add_argument("--dev-frac", type=float, default=0.6)
    b.add_argument("--seed", type=int, default=42)
    b.set_defaults(fn=cmd_build)
    g = sub.add_parser("grep")
    g.add_argument("pattern")
    g.add_argument("--processed", default=str(ROOT / "data/processed"))
    g.add_argument("--accent-insensitive", action="store_true")
    g.add_argument("--max", type=int, default=20)
    g.set_defaults(fn=cmd_grep)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
