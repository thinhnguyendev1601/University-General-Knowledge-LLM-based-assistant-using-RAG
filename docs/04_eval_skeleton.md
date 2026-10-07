# Evaluation skeleton — how it works and how to use it

## 1. What exists today
```
core/schemas.py            data contracts (Chunk, AnswerResult, TestQuestion, …)
core/textnorm.py           canonical text normalisation used everywhere
scripts/extract_text.py    raw PDF/DOCX → data/processed/<doc_id>.txt + .pages.json (+ quality warnings)
eval/testset.py            annotations CSV → validated, quote-resolved, split JSONL  (+ `grep` helper)
eval/metrics.py           pure metric functions (retrieval, refusal, citation, key facts)
eval/run_eval.py           run one config over the test set, save everything
eval/compare.py            runs → markdown comparison table
eval/sweep_gate.py         offline threshold sweep for the refusal gate
eval/pipeline_stub.py      throw-away baselines: keyword, oracle (must score 1.0), always-refuse
tests/                     metric unit tests + an end-to-end smoke test (fake corpus)
```

## 2. Daily commands
```bash
python scripts/extract_text.py                      # raw → canonical text (+ quality table)
python -m eval.testset grep "cảnh báo" --accent-insensitive
python -m eval.testset build                        # CSV → eval/questions/testset.jsonl (errors block the write)
python -m eval.run_eval --config eval/config.example.yaml           # dev split
python -m eval.run_eval --config eval/configs/final.yaml --final    # test split (logged)
python -m eval.compare eval/runs/<a> eval/runs/<b>  # paste into the report
python -m eval.sweep_gate eval/runs/<dev-run-with-gate-off>
pytest                                              # must stay green
```

## 3. One run = one config file
A run is fully defined by a YAML file (`eval/config.example.yaml`): test set, split, pipeline import path, pipeline kwargs, `k_values`, `min_overlap_frac`. Copy it to `eval/configs/<experiment>.yaml` for each experiment — **one experiment, one file, committed to Git**. The run folder stores the config snapshot, git commit (`+dirty` if uncommitted changes), test-set hash and per-question results, so any number in the report can be reproduced and traced.

Plugging in the real pipeline: write `build_pipeline(**kwargs)` returning an object with `answer(query) -> AnswerResult`, then set `pipeline: your_pkg.module:build_pipeline`. To test the harness itself use the oracle (`eval.pipeline_stub:build_oracle`, every retrieval/answer metric must be 1.0) and `build_always_refuse` (refusal recall 1.0, everything else 0).

## 4. Metrics — what they mean and how to read them
| Metric | Definition | Read it as |
|---|---|---|
| `hit@k` | Share of answerable questions where a top-k chunk covers ≥ `min_overlap_frac` (default 50%) of at least one evidence span | Did retrieval put the right passage in front of the generator? |
| `evidence_recall@k` | Fraction of evidence spans covered by top-k chunks (matters for multi-section/doc) | Did we get *all* the needed passages? |
| `mrr` | Mean reciprocal rank of the first covering chunk | How high does the right chunk rank? |
| `key_fact_recall_when_answered` | Fraction of `key_facts` present in the answer (case/space-insensitive, **diacritic-sensitive**) | Cheap proxy for correctness |
| `answer_accuracy_auto` | Answerable question: answered **and** all key facts present **and** no forbidden fact. Unanswerable: refused | Headline behaviour metric (a proxy — see §6) |
| `refusal_precision / recall / F1` | Treat "refused" as the positive class against `answerable=False` | Does the gate refuse the right things? |
| `false_refusal_rate` | Refused / answerable questions | Cost of over-caution |
| `unsupported_answer_rate` | Answered / unanswerable questions | **Hallucination-risk proxy — the number this project exists to push down** |
| `citation_coverage` | Answered answerable questions that carry ≥ 1 citation | Are answers attributed at all? |
| `quote_verified_rate` | Cited quote is a verbatim substring of the cited chunk (and the chunk was retrieved) | Catches fabricated citations mechanically |
| `citation_precision / recall` | Cited chunks that cover evidence / evidence covered by cited chunks | Are the shown sources the right ones? |
| `latency_ms_*` | Mean, p50, p95 | Cost of extra grounding layers |

Every metric is also broken down `by_category` and `by_lang` in `summary.json`. Always look at the breakdown before celebrating an average: refusal gates typically win on `out_of_domain` and lose on `absent_in_domain` / `false_premise`; Vietnamese and cross-lingual questions usually trail English.

## 5. Discipline (what makes the numbers credible)
- **Dev vs test:** tune on `dev` only. `run_eval` refuses `test`/`all` without `--final` and appends every such run to `eval/runs/test_runs.log`. Run test once per *finished* configuration.
- **Frozen test set:** at freeze (week 5) set every row to `approved`, then use `min_status: approved` in final configs. Later fixes to questions are logged in Git with a reason.
- **No leakage:** do not paste test questions into prompts, few-shot examples or threshold tuning. Regression cases from the feedback button go to a separate file.
- **Report the failures:** keep the per-question `results.jsonl`; the error analysis (which categories/languages fail and why) is worth more than another decimal on the average.
- **Costs:** log which LLM/embedding model each run used (put it in the config, e.g. `pipeline_kwargs`).

## 6. Known limits of this skeleton (deliberate — build in weeks 5–8)
1. **`answer_accuracy_auto` is a key-fact proxy.** It can be fooled by verbose answers that contain the key facts alongside wrong claims, and it can miss correct paraphrases without the key strings. Validate it: hand-label ~30 answers, compare with the proxy.
2. **No LLM judge yet.** Week 7: add faithfulness (claim-level support by the cited chunks) and answer-correctness judges. Before trusting a judge, measure its agreement with your hand labels on that same ~30-item set and report it. Never use the same model call to generate and to grade an answer.
3. **`false_premise` correction** is scored as refusal only (see annotation guide §6).
4. **One score per question:** no confidence intervals. With ~40 test questions, differences under ~5–8 points are noise; report counts next to percentages, and use bootstrap intervals in the final write-up.
5. **Retrieval hit** counts a chunk that covers ≥ 50% of the evidence span. Tune `min_overlap_frac` only in the config and only for all runs at once.

## 7. Ablation plan expressed as configs (suggested file names)
`eval/configs/`: `01_dense_fixed.yaml` → `02_dense_struct.yaml` → `03_hybrid.yaml` → `04_hybrid_rerank.yaml` → `05_gate.yaml` → `06_gate_quotecheck.yaml` → `07_gate_quotecheck_faith.yaml`; side branches `emb_bge-m3.yaml` vs `emb_me5.yaml`, `llm_small.yaml` vs `llm_large.yaml`. `python -m eval.compare` on the dev runs gives the ablation table; final test runs only for the configurations you will report.

## 8. Fast sanity checks when numbers look wrong
- Oracle not at 1.0 → bug in the harness or a stale test set (rebuild).
- `hit@k` = 0 for everything → wrong `doc_id`s, or chunks not built from the canonical text (`verify_chunk`).
- Sudden metric jump after a rebuild → check `testset_sha256` in `meta.json`.
- Vietnamese key facts never match → diacritics normalisation (NFC) or a legacy-font extraction problem.
