# Week 1 checklist — Eval & Grounding lead

Goal for today: teammates can (a) find and open the corpus, (b) start writing test questions
next week from a clear guide, and (c) you can already score *any* pipeline with one command.

## Definition of done
- [ ] Kit unpacked into the repo, `pip install -r requirements.txt`, `pytest` → 7 passed
- [ ] ≥ 8 documents downloaded to `data/raw/`, named `<doc_id>.pdf|docx` exactly as in `data/manifest.csv`
- [ ] `data/manifest.csv` complete for those rows (language, pages, text layer, hash, status checked)
- [ ] `python scripts/extract_text.py` runs clean (or every warning is understood and noted in `notes`)
- [ ] You wrote ~10 pilot questions in `eval/questions/annotations.csv`; `python -m eval.testset build` passes
- [ ] `python -m eval.run_eval --config eval/config.example.yaml` prints first baseline numbers
- [ ] Guides shared with the team (01 corpus, 03 annotation) and the sheet template created

## Suggested order (time-boxed)
| Step | Time | What |
|---|---|---|
| 1 | 15 min | Unpack kit, install deps, run `pytest`. Add `.gitignore.snippet` lines to your `.gitignore`. |
| 2 | 60–75 min | Download documents. Start with the 3 direct-PDF rows (`moet-tt08-2021`, `iu-acad-reg-2021`, `iu-scse-handbook-2024`), then the hub-page rows. Ask one teammate to fetch the two hold-out documents in parallel. |
| 3 | 20 min | Fill in the manifest as you go (do not batch it at the end). |
| 4 | 15 min | `python scripts/extract_text.py`; read the warnings table. |
| 5 | 20 min | Spot-check canonical text: `python -m eval.testset grep "cảnh báo học vụ"`; open one `.txt` and one `.pages.json`. Check Vietnamese diacritics look right. |
| 6 | 30–40 min | Write ~10 pilot questions (see mix below), run `build`, then `run_eval` on the keyword baseline. |
| 7 | 10 min | Message the team: where the guides are, which doc each person will "own" for question writing next week. |

## Pilot question mix (only for validating tooling — the real set is written by the team)
2 single_fact (vi) · 2 single_fact (en) · 1 cross_lingual · 1 table_numeric · 1 version_conflict ·
2 unanswerable (1 absent_in_domain, 1 holdout_only) · 1 adversarial

## If time runs short, cut in this order
1. Hold-out documents (need only the manifest rows + files by next week)
2. Documents 6–8 from the hub page (keep ≥ 5 indexed docs today)
3. Pilot questions (keep ≥ 4: one answerable, one unanswerable, one Vietnamese, one English)

Never cut: manifest completeness for downloaded docs, and the `pytest` + `run_eval` smoke run.

## Tell teammates
- Never edit `data/processed/*` or rename `doc_id`s — offsets and test questions depend on them.
- Test questions are written in the sheet, exported to `eval/questions/annotations.csv`; only the eval lead runs `build`.
- The TEST split is not for tuning. `run_eval` refuses it without `--final`, and every final run is logged.
