# Improvement guide and learning plan

Written 2026-10-07. Companion to `docs/05_code_walkthrough.md`. Three parts:

- **A.** What to improve in the kit, prioritized, each with evidence from this corpus and
  a way to test the fix. No solutions are written out — hints only. Write the first
  version yourself, then ask for a review.
- **B.** The learning loop: predict → run → explain. Exercises with hidden answers.
- **C.** Building the RAG core one step at a time, with a hypothesis log.

---

## A. Improvements, in priority order

Each item: **what's wrong (verified)** → **why it matters** → **hint** → **how you'll know it works**.

### P0 — fix before the test set grows past ~30 questions

**A1. `eval.testset grep` has no role filter.**
It searches every `.txt`, including `holdout` and `excluded` documents. On 2026-09-22,
`grep "cảnh báo học vụ"` returned 4 hits — all in a holdout document, 0 in the indexed
corpus. Absence proofs (`absent_in_domain`, `false_premise`, `holdout_only`) are only valid
against `role=indexed` text.
*Hint:* `--role` (default `indexed`) plus `--manifest`; reuse `load_manifest`.
*Test:* `grep "cảnh báo học vụ"` → 0 hits; `--role holdout` → 4 hits.

**A2. `KeywordBaseline` (and later your pipeline) indexes every `.txt`.**
`eval/pipeline_stub.py` loads all of `data/processed/` unless `docs=` is passed, so a
baseline run can retrieve from holdout and excluded files and "answer" `holdout_only`
questions. This is the same bug as A1 in a more damaging place: it silently raises
the score.
*Hint:* build the document list from the manifest's `indexed` rows; fail loudly when a
holdout doc_id appears in `retrieved`.
*Test:* predict TM-012's result before and after.

**A3. Key-fact matching is substring matching.**
`fact_present("108", "1080")`, `fact_present("1,0", "11,0")`,
`fact_present("7 weeks", "17 weeks")` are all `True` (verified). TM-002's key fact is
exactly this shape.
*Hint:* when a fact starts or ends with a digit, require a non-digit (or string edge) on
that side. Keep the rest substring-based, because Vietnamese words are multi-syllable.
*Test:* write the three cases above as unit tests first; they must fail before your fix.

**A4. No key facts ⇒ auto-correct.**
`key_fact_recall([], answer) == 1.0` (verified), so an answerable question with no key
facts is `auto_correct` whenever the system answers anything. Build only *warns*.
*Hint:* make it an error for answerable questions, or exclude such questions from
`answer_accuracy_auto` and report the count.

**A5. `extract_text.py` warnings miss three failure types seen in this corpus.**
(a) no `vi_diacritic_ratio` check (`vnuhcm-student-affairs-953-2019` printed `ok`);
(b) averages hide blank pages (`moet-tt56-2026`: pages 18–24 empty, printed `ok`);
(c) lost word spaces (`hcmus-student-handbook-2025`, 81+ glued tokens, printed `ok`).
*Hint:* (a) needs the manifest's `lang` (see the September walkthrough in the chat log);
(b) compute per-page character counts and report pages below a floor; (c) count tokens
that are much longer than the language's normal maximum.
*Test:* each guard should flag exactly its document and nothing else in the corpus.
Note how the doc in (c) has a healthy diacritic ratio — guards cover each other.

### P1 — before the first real ablation (week 4–5)

**A6. Retrieval metrics don't penalize retrieving too much.**
`covers()` divides by evidence length; a whole-document chunk scores `hit@1 = 1.0`
(verified). A chunking ablation can "win" by making chunks bigger.
*Hint:* report what the generator had to read: mean characters (or tokens) in the
top-k, alongside hit@k. Optionally a precision-style number: evidence chars ÷ retrieved chars.
*Test:* a whole-document pipeline should look perfect on hit@k and terrible on the new number.

**A7. Identical text in a version pair counts as a miss.**
TM-003's evidence sentence is verbatim in both SCSE handbooks; retrieving the 2023 copy
scores 0. Every version pair will do this, and you now have two (SCSE, HCMUS).
*Hint:* at build time, for each evidence span, find verbatim copies in other indexed
docs of the same `version_group` and record them as acceptable alternatives — but not for
`version_conflict` questions, where retrieving the stale copy is exactly the failure.

**A8. Quote verification proves existence, not support.**
A citation quoting `"the"` verifies (verified). A model can game `quote_verified_rate`
with tiny quotes.
*Hint:* minimum quote length (characters or tokens), and/or require the quote to overlap
the evidence span. Report how many citations were too short.

**A9. Crashes look like hallucinations.**
`evaluate_one` records a crash as `refused=False`; for an unanswerable question
`summarize` counts that as an unsupported answer. A buggy pipeline inflates the project's
headline number.
*Hint:* exclude `error` records from the confusion matrix and report them separately.

**A10. `forbidden_hit` can't tell "asserts" from "mentions".**
TM-008: "108 credits (the 2023-24 handbook said 120)" trips `forbidden_facts=120`. Fine
for v1 — but count how often it happens before you trust `forbidden_fact_rate`. This is
the LLM-judge's job in week 7.

### P2 — polish, and good interview stories

**A11. Normalization gaps.** Ligatures (70 in `gatech-cs-catalog-2026`), soft hyphens (20),
en dashes (259) survive `normalize_text`; dehyphenation runs before whitespace cleanup
(`self-\npreparation`). Any change here changes canonical text: do it once, deliberately,
with a `doc_version` bump for every affected document and a rebuild. Measure: how many
evidence quotes move from `fuzzy` to `exact`?

**A12. `resolve()` returns the first of multiple occurrences.** Record all occurrences and
error if the quote is ambiguous instead of warning.

**A13. Split stickiness lives in `testset.jsonl`.** Commit it. Consider storing the split in
the annotation CSV once frozen (week 5) so it can't be lost.

**A14. Document-quality guards for `excluded` text.** `load_doc_texts` and the baseline
happily read excluded files. Once A1/A2 exist, consider not writing `.txt` for excluded
docs at all, or writing them to a separate folder.

---

## B. The learning loop — predict, run, explain

Rule: write your prediction in `eval/HYPOTHESES.md` (template in §C) **before** running.
Then open the answer. A wrong prediction is the valuable outcome — write one line on what
you misunderstood.

### B1. Sanity of the harness
Build the pilot test set (`python -m eval.testset build`), then run `eval.run_eval` with
three configs: `build_oracle`, `build_always_refuse`, `build_keyword_baseline`
(copy `eval/config.example.yaml`; the oracle and always-refuse take different kwargs —
read their build functions).

Predict for each: `hit@5`, `answer_accuracy_auto`, `refusal_recall`,
`false_refusal_rate`, `unsupported_answer_rate`.

<details><summary>What to expect (open after predicting)</summary>

- Oracle: every retrieval metric 1.0; refusal recall 1.0, false refusals 0. If anything
  is below 1.0, the harness or a question is broken — find out which.
- Always-refuse: refusal recall 1.0, false_refusal_rate 1.0, answer accuracy 0;
  retrieval metrics are 0 because it retrieves nothing.
- Keyword baseline: the interesting one. Look at TM-012 (holdout_only) specifically and
  connect what you see to improvement A2.
</details>

### B2. Break it on purpose

**NFD.** Convert TM-001's quote to NFD (`unicodedata.normalize("NFD", q)`), put it in a
copy of the CSV, rebuild. Predict: does it resolve?

<details><summary>Answer</summary>

It resolves `exact`, because `resolve()` normalizes the quote first. Now try
`nfd in canonical_text` directly: `False`, and `len(nfd)` is 90 vs 70. The kit is robust
*because* normalization is centralized. Your chunker will be robust only if it also
normalizes before computing offsets. Where in your own future code could NFD sneak in?
</details>

**Overlap threshold.** Change `min_overlap_frac` to 0.9 and 0.1 in a keyword-baseline
config. Predict which questions flip on `hit@5`.

<details><summary>What to look at</summary>

Questions with short evidence (TM-002, TM-007: one short line) vs long evidence
(TM-005 ev2, TM-003 ev1). Paragraph chunks of up to 1,200 chars easily cover a short
span fully, but can cut a long span in half. Write down which evidence lengths are
sensitive — that informs your chunk size.
</details>

**Corrupt an offset.** Make a `Chunk` whose `text` doesn't equal
`canonical[char_start:char_end]` and call `verify_chunk`. Then try building one whose
`chunk_id` doesn't match its offsets. Predict which check fires first in each case.

<details><summary>Answer</summary>

`verify_chunk` raises `AssertionError` for the text mismatch. For the id mismatch, you
never reach `verify_chunk`: the Pydantic `model_validator` in `Chunk` raises at
construction. Two layers, two different failure messages.
</details>

**Delete a key fact.** Remove TM-002's key fact and run the keyword baseline. Predict
`answer_accuracy_auto` for TM-002.

<details><summary>Answer</summary>

If the baseline answers at all, it is auto-correct, because `key_fact_recall([]) == 1.0`.
Build only warns. This is improvement A4.
</details>

**Whole-document chunk.** Write a 10-line pipeline that returns one chunk per document
(the whole text) for every query. Predict `hit@1`, `hit@5`, MRR.

<details><summary>Answer</summary>

Near-perfect retrieval metrics whenever the right document is ranked first. This is
improvement A6, and the reason "context size" belongs next to hit@k in every table.
</details>

**Splits.** Find a set of questions where building them in two batches gives different
splits from building them all at once. (Hint: you need ≥2 new questions in the same
category in the second batch.) Then explain why it matters that `testset.jsonl` is
committed.

### B3. Read real failures before building
Run the keyword baseline and read `results.jsonl` for 5 questions it gets wrong. For each,
classify the cause using the cascade from the September walkthrough: extraction /
chunking / retrieval / context / generation / evaluation. Expect several to be
"evaluation" — the metric was wrong, not the system.

---

## C. Building the RAG core — one step, one hypothesis, one run

Order (from your instruction file; each step is a new pipeline config, so every earlier
step stays reproducible):

| Step | Build | A hypothesis worth testing (write your own) |
|---|---|---|
| 1 | Structure-aware chunker: Điều/Khoản/Article splitter for regulations, heading splitter for handbooks; `section_path` filled; `verify_chunk` on every chunk | "evidence_recall@5 rises on multi_section vs paragraph chunks, because each Điều stays whole" |
| 2 | Dense retrieval (bge-m3), `embedding_text()` = section path + text | "TM-007 (CS total credits, heading 80 lines above) is found only when section_path is embedded" |
| 3 | BM25 with a Vietnamese word segmenter | "BM25 beats dense on exact identifiers ('Điều 11', '719/QĐ-ĐHQT') and loses on TM-001's 'học vụ' vs 'học tập'" |
| 4 | Fusion (RRF) | "fusion ≥ max(dense, BM25) on hit@5 for both languages" |
| 5 | Reranker | "MRR rises more than hit@10 — the reranker reorders, it doesn't find" |
| 6 | Refusal gate, threshold from `sweep_gate.py` on **dev** | "unsupported_answer_rate on holdout_only drops more than on absent_in_domain" |
| 7 | Quote verification in the pipeline (downgrade to refusal if a cited quote isn't in the chunk) | "quote_verified_rate → 1.0 with a small rise in false_refusal_rate" |

New in this corpus and worth a hypothesis of its own: **institution scope.** IU, UIT,
HCMUS and MOET all have rules on warnings, grading and credits, with different numbers
(TM-001, TM-004 notes). Predict how often retrieval returns the wrong institution's rule
— then decide whether metadata filtering (pgvector, the reason it was chosen) belongs in
the pipeline.

### `eval/HYPOTHESES.md` template — one entry per run

```markdown
## 2026-10-__  run: <run_id>   config: eval/configs/<name>.yaml   split: dev
Change: <one sentence — what is different from the previous run>
Hypothesis: <metric> will <rise/fall> on <slice>, because <mechanism>.
Prediction: <number or direction, written BEFORE running>
Result: <the numbers>
Verdict: confirmed / refuted / inconclusive (n too small?)
Explanation: <why — name the questions that moved and look at their traces>
Next: <what this suggests trying>
```

This log — hypothesis, result, explanation, with real numbers — is the strongest
interview material this project can produce. A refuted hypothesis with a good
explanation is worth more than a confirmed one.

---

## D. Using Claude on this project without vibe coding

From your instruction file, with concrete prompts that work:

- **You write v1, Claude reviews.** "Here's my `fact_present` fix for A3. Find inputs that
  break it — Vietnamese and English, decimals with `,` and `.`." Don't ask for the fix.
- **Ask for counterexamples, not implementations.** "Give me five chunk boundaries that
  would break `verify_chunk` in non-obvious ways."
- **Ask for tests that should fail first.** "Write unit tests for A3 that fail on the
  current code." Run them red, then make them green yourself.
- **Delegate outside your lane freely:** Docker, CI, CRUD, the Streamlit mock UI.
- **Explain-back test.** Before moving on from any function, explain what it does and why
  without looking. If you can't, it isn't yours yet.
