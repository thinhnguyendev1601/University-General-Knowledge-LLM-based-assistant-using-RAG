# Code walkthrough — the eval-lead core (textnorm, quote resolution, splits, metrics)

Written 2026-10-07 for Tommy. Scope: the four pieces that need human understanding
before anything is built on top of them — `core/textnorm.py`, the quote-resolution half
of `eval/testset.py`, the dev/test split logic, and `eval/metrics.py`. Line numbers are
from the files as of this date; if they drift, search for the function name.

Every behaviour marked **(verified)** was run against the real corpus on 2026-10-07, not
inferred from reading. Read `docs/06_improvement_guide.md` next for what to change.

How to use this doc: read one section, close it, then explain the function out loud
without looking (the explain-back test). Anything you can't explain isn't yours yet.

---

## 0. The whole flow on one screen

```
data/raw/<doc_id>.pdf
   │  scripts/extract_text.py  (PyMuPDF page text → normalize_text per page → join with "\n\n")
   ▼
data/processed/<doc_id>.txt        ← CANONICAL TEXT. Every offset in the project points in here.
data/processed/<doc_id>.pages.json ← page_starts, text_sha256, text_quality()
   │
   ├── eval/testset.py build:  annotations.csv ─► row_to_question ─► validate ─► DocText.resolve(quote)
   │                                                                       │       → (char_start, char_end)
   │                                                     assign_splits ◄───┘
   │                                                           ▼
   │                                          eval/questions/testset.jsonl  (questions + resolved spans + split)
   │
   └── your pipeline: chunk(canonical) ─► retrieve ─► answer() → AnswerResult
                                                              │
        eval/run_eval.py: evaluate_one(q) ◄──────────────────┘
             retrieval_metrics(res.retrieved, q.evidence)   span overlap, no chunk IDs
             key_fact_recall(q.key_facts, res.answer)        string presence
             citation_metrics(res, q.evidence)                quote ⊂ cited chunk?
             ▼
        summarize(records) → summary.json (overall / by_category / by_lang)
```

The one idea that holds it together: **the test set never stores chunk IDs.** It stores
verbatim quotes, resolved to character spans in the canonical text at build time. Your
chunker returns chunks with `char_start/char_end` into the same text. Metrics compare
*spans*, so you can change the chunker every week without relabelling a single question.

---

## 1. `core/textnorm.py` — the canonical form of text

Rule (top of file): anything compared, offset-indexed or hashed goes through these
functions first. Vietnamese is the reason: the same visible "ạ" can be one code point
(NFC) or two (NFD: "a" + combining dot), and PDF extractors emit both.

### `normalize_text(s)` — line 24 — the canonical-text transform

Applied by `extract_text.py` to each page. Steps, in order:

| # | Step | Example | Why |
|---|---|---|---|
| 1 | `unicodedata.normalize("NFC", s)` | "a"+U+0323 → "ạ" | one representation per glyph |
| 2 | NBSP→space; remove zero-width space and BOM | | invisible chars break `in` checks |
| 3 | U+2010, U+2011 (hyphen variants) → "-" | | |
| 4 | `_SOFT_HYPHEN_BREAK` + `_dehyphenate` (line 19) | "regu-\nlation" → "regulation" | rejoin words split at line end, but only if the next char is lowercase ("Vietnam-\nHCM" stays) |
| 5 | runs of spaces/tabs → one space | | |
| 6 | strip spaces around newlines | | |
| 7 | 3+ newlines → 2 | | |
| 8 | `.strip()` | | |

What to expect **(verified)**:
- Step 4 runs *before* step 6, so `"self- \npreparation"` (a space before the newline)
  does not match and ends as `"self-\npreparation"` in `iu-acad-reg-2021`. A quote typed
  as "self-preparation" resolves only fuzzily (`fuzzy:98`).
- Not handled: soft hyphen U+00AD (20 in the corpus), en dash U+2013 (259), minus U+2212
  (7), typographic ligatures `ﬁ ﬂ` (70 in `gatech-cs-catalog-2026`). NFC does **not**
  unfold ligatures; NFKC would (`"ﬁeld"` → `"field"`).
- Output is **frozen per `doc_version`**. Changing this function changes canonical text,
  which changes `sha256_text`, which can move every evidence span. That's why you bump
  `doc_version` and rebuild instead of editing it quietly.

### `collapse_ws(s)` — line 36
NFC + every whitespace run (incl. newlines) → one space. This makes quote matching
whitespace-insensitive: the line breaks in a quote you copy never matter.

### `match_form(s)` — line 41
`collapse_ws(s).casefold()`. Used by the metrics to compare answers with key facts and
quotes with chunks. **Keeps diacritics on purpose**: "học phí" ≠ "hoc phi", because
removing them merges different Vietnamese words.

### `strip_accents(s)` — line 47
NFD, drop combining marks, map đ→d. Only for accent-insensitive search and for detecting
no-diacritics user input. Never for storage.

### `sha256_text` / `sha256_file` — lines 54, 58
Hash of canonical text (UTF-8) / of the raw file. These are what the manifest's
`sha256_text`/`sha256_raw` pin. The duplicate UMN/VNU download was caught this way.

### `text_quality(text, n_pages)` — line 72
Cheap numbers used by `extract_text.py::warn()`:
`n_chars`, `chars_per_page` (**an average over the whole document**),
`vi_diacritic_ratio` (Vietnamese-marked letters / all letters), `replacement_chars`
(U+FFFD count), `non_letter_ratio`.

What the numbers can and can't see **(verified on this corpus)**:

| Failure | Caught by | Missed by |
|---|---|---|
| Pure scan, no text (`iu-qd266-scholarship`) | `chars_per_page` | — |
| Scan + OCR without Vietnamese (`vnuhcm-student-affairs-953-2019`, 41k chars) | `vi_diacritic_ratio` = 0.0000 — **but `warn()` never checks it** | everything `warn()` does check → printed "ok" |
| Scan whose only text is a signature stamp (`nd81` candidate, rejected) | `chars_per_page` ≈ 3 | `vi_diacritic_ratio` = 0.18 looks healthy |
| 7 blank pages inside a 24-page doc (`moet-tt56-2026`) | nothing — needs a per-page check | `chars_per_page` average = 1,593 → "ok" |
| Lost word spaces (`hcmus-student-handbook-2025`) | nothing | all of them |

Lesson: each guard has a blind spot that another guard covers. Average-based metrics
hide local failures.

---

## 2. Quote resolution — `eval/testset.py` lines 42–84

### `_collapse_with_map(text)` — line 42
Builds two things in one pass over the canonical text:
- `collapsed`: the text with every whitespace run replaced by one space (leading
  whitespace dropped);
- `idx`: for each character of `collapsed`, its index in the original text.

Worked example:

```
text      = "Điều 1.\n\n  Phạm vi"
index       0123456 7 8 9 10...
collapsed = "Điều 1. Phạm vi"
idx       = [0,1,2,3,4,5,6, 7, 11,12,13,14,15,16,17]
                              ^ the single space maps to the FIRST whitespace char (7)
```

So a match found in `collapsed` at positions `[p, p+len)` maps back to the canonical span
`[idx[p], idx[p+len-1] + 1)`. Note `+1` after the *last matched character*, not
`idx[p+len]` — that would swallow trailing whitespace.

### `DocText.resolve(quote)` — line 62
1. Normalize the quote exactly like document text: `collapse_ws(normalize_text(quote))`.
2. `collapsed.find(q)` — exact substring. If found, look for a second occurrence:
   note `"exact"` or `"multiple"`. **On `multiple` it returns the FIRST occurrence**, which
   may not be the one you meant — that's why build warns "lengthen it".
3. Else `rapidfuzz.fuzz.partial_ratio_alignment(q, collapsed, score_cutoff=90)` — finds
   the best-matching window ≥ 90% similar. Note `"fuzzy:<score>"`.
4. Else `"not_found"`.

What to expect **(verified)**:
- An NFD quote resolves **`exact`** — step 1 normalizes it. A naive `quote in text` on the
  same NFD string returns `False`, and the NFD string is 20 chars longer (90 vs 70), so
  any code that computes offsets on un-normalized text is off by that much.
- Paraphrase / ellipsis (`"... dưới 1,0 ..."`) → `not_found`. Fuzzy tolerates typos, not
  rewording.
- Resolution is per document. The same sentence in two documents (version pairs!) is
  not a "multiple" warning — but see §4 for what it does to metrics.

### `validate(q, docs, manifest)` — line 149 — the rules a question must pass

| Rule | Error or warning |
|---|---|
| `unanswerable`/`adversarial` ⇔ `answerable=FALSE`, `unanswerable_type` set; adversarial ⇒ `prompt_injection` | error |
| answerable ⇒ `gold_answer` + ≥1 evidence | error |
| answerable with no `key_facts` | **warning only** (see §4: auto-correct becomes trivially true) |
| `multi_section`/`multi_doc` ⇒ ≥2 spans; `multi_doc` ⇒ ≥2 doc_ids | error |
| `version_conflict` ⇒ `forbidden_facts` | error |
| each key fact (any `|` alternative) must appear in `gold_answer` | warning |
| evidence doc not in manifest | error |
| answerable citing a doc whose `role != indexed` | error |
| `holdout_only` citing a doc whose `role != holdout` | error |
| quote > 600 chars | warning |
| quote `not_found` | error; `multiple`/`fuzzy` → warning |
| `cross_lingual` whose question lang equals every evidence doc's lang | warning |
| adversarial with no obvious injection phrase | warning |
| duplicate id / duplicate question text; reviewed/approved without a different reviewer | error (in `cmd_build`) |

`row_to_question` (line 121) parsing details worth knowing: `key_facts` split on `||`,
alternatives inside a fact on `|`; `tags` accept `;` or `,`; `answerable` accepts
TRUE/yes/y/1 and FALSE/no/n/0; `page` is kept only if it is all digits.

---

## 3. Dev/test splits — `assign_splits`, line 220

Goal: ~60% dev / 40% test, balanced **within each category**, and an assignment never
changes once made.

Algorithm:
1. Read the existing `testset.jsonl` (if any): `id → split`. Those questions keep their
   split and are counted per category.
2. Sort the NEW questions by `_h(seed, id)` (line 216: first 8 hex chars of
   `sha256(f"{seed}:{id}")`) — a deterministic pseudo-random order.
3. For each new question, look at its category's current counts and compute how far the
   dev fraction would be from `dev_frac` if it went to dev vs to test. Pick the closer.
   On an exact tie, use `_h % 100 < dev_frac*100`.

What to expect:
- Stickiness lives in **the output file**. Delete `testset.jsonl` and every question is
  "new" again. `.gitignore` does *not* exclude it — commit it, or teammates rebuilding from
  scratch can get different splits.
- A question whose category changes keeps its old split (counts drift a little).
- A question removed from the CSV disappears from the output — its split is forgotten.
- Small categories are lumpy: with 1 question per category, the first always goes to
  dev (1/1 = 1.0 is closer to 0.6 than 0/1 = 0.0). That's why the pilot build shows
  `1/0` for most categories.
- In a test on 2026-10-07, building 12 questions then adding 1 gave the same splits as
  building all 13 at once — but that case had one question in the affected category, so
  it proves nothing general (exercise in docs/06).

---

## 4. `eval/metrics.py` — what each number really measures

### Span helpers — lines 17–29
`covers(sc, ev, min_frac=0.5)`: same `doc_id` **and**
`overlap(chunk, evidence) / len(evidence) ≥ min_frac`.
The denominator is the **evidence** length, never the chunk length.

**(verified)** A single chunk containing all of `iu-acad-reg-2021` (63,795 chars) scores
`hit@1 = 1.0`. Bigger chunks can only raise hit@k. Nothing in the metrics penalizes
retrieving too much text — keep that in mind before celebrating a chunking ablation.

### `retrieval_metrics` — line 32
Sorts by `rank`, then:
- `rr` = 1/rank of the first chunk covering **any** evidence span (0 if none) → MRR when averaged;
- `hit@k` = 1 if any evidence span is covered by the top-k;
- `evidence_recall@k` = fraction of evidence spans covered by the top-k (matters for
  `multi_section`/`multi_doc`, where hit@k can be 1 while half the evidence is missing).

**Same sentence, different document = miss.** TM-003's evidence sentence is verbatim in
both SCSE handbook editions; a retriever returning the 2023 copy scores 0 although the
answer would be identical. Every version pair has this property.

### Answer metrics — lines 58–73
- `fact_present(fact, answer)`: any `|`-alternative, in `match_form`, is a **substring** of
  the answer.
- `key_fact_recall(facts, answer)` = fraction present. **Empty list → 1.0.**
- `forbidden_hit(forbidden, answer)` = any forbidden fact present.

**(verified)** substring means: `"108"` ⊂ `"1080"`, `"1,0"` ⊂ `"11,0"`,
`"7 weeks"` ⊂ `"17 weeks"` — all `True`. And `forbidden_hit` cannot tell
"the answer is 120" from "it used to be 120, now 108".

### `citation_metrics` — line 76
- `quote_verified_rate` = cited quotes that are substrings (`match_form`) of the cited
  chunk's text ÷ number of citations. Citations pointing at a chunk that was never
  retrieved count in the denominator but can't verify.
- `citation_precision` = cited chunks covering some evidence ÷ citations.
- `citation_recall` = evidence spans covered by some cited chunk.

**(verified)** a citation whose quote is just `"the"` verifies (rate 1.0). The check proves
the quote *exists* in the chunk, not that it *supports* the answer.

### `summarize` — line 120 — the refusal confusion matrix
The positive class is **"should refuse"**:

| | system refused | system answered |
|---|---|---|
| unanswerable question | TP — correct refusal | **FN — unsupported answer** |
| answerable question | **FP — false refusal** | TN |

- `refusal_precision` = TP/(TP+FP), `refusal_recall` = TP/(TP+FN)
- `false_refusal_rate` = FP / #answerable — cost of over-caution
- `unsupported_answer_rate` = FN / #unanswerable — **the number the project exists to push down**
- `answer_accuracy_auto` = mean over answerable of `auto_correct`, where (in
  `run_eval.evaluate_one`) `auto_correct = answered and key_fact_recall == 1.0 and not forbidden_hit`.
- Retrieval averages use only answerable questions; citation averages only answered
  answerable ones.

What to expect: a question that **crashes** the pipeline is recorded with
`refused=False`. For an unanswerable question that counts as FN — a crash looks exactly
like a hallucination in `unsupported_answer_rate`. Check `n_errors` before reading it.

`summarize_by(records, key)` runs the same thing per category / per language.

---

## 5. What's yours to write, and what to leave alone

| Leave as-is (contracts other people depend on) | Yours to build (the RAG core) |
|---|---|
| `Chunk`/`EvidenceSpan`/`AnswerResult` field names and `make_chunk_id` | structure-aware chunker (Điều/Article splitter + heading splitter for handbooks) |
| `normalize_text` — change only with a `doc_version` bump and rebuild | dense retrieval, BM25 with Vietnamese segmentation, fusion, reranker |
| quote-resolution semantics (quotes are truth, spans are derived) | refusal gate (`sweep_gate.py` already sweeps it offline) |
| split stickiness | quote verification inside the pipeline (metrics already check it after the fact) |
| | the improvements in docs/06 — each one is small and testable |

A pipeline is anything with `.answer(query) -> AnswerResult`, returned by a build
function named in the run config as `"your_pkg.module:build_fn"`. Fill `retrieved` with
what the generator actually saw — retrieval metrics are computed from it.
