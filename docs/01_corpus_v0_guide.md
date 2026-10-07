# Corpus v0 — sources, collection procedure, manifest format

## 1. Principles
1. **Provenance over prestige.** "Certified by a well-known university" is not a formal status. What we can prove is *who published the file*. Every document must come from the issuing institution's own domain (tier A), or from an official mirror (tier B). Commercial law-aggregator sites are tier C: use only as a pointer, never as the corpus copy.
2. **Currency matters.** Handbooks and regulations get replaced. Record `doc_status` and the date you checked (`status_checked_on`). Old versions are not junk — a *superseded* document plus its current version is exactly what we need to test conflict handling.
3. **Bilingual on purpose.** HCMIU teaches in English but many binding rules are issued in Vietnamese. Real students ask in both. The corpus should mix languages, and includes a possible vi/en parallel pair.
4. **Hold out a few documents.** Documents with `role=holdout` are never indexed. Questions whose answer is only in them are the best "plausible but unanswerable" test.
5. **Do not redistribute.** Keep `data/raw/` and `data/processed/` out of Git. Commit the manifest and a download list instead. If the repo may become public, remove evidence quotes from the test set first (they are excerpts of the source documents).

## 2. Corpus v0 — 10 rows already seeded in `data/manifest.csv`
Links below appeared in search results while preparing this kit. **Open each one, confirm it loads and is the current edition, then record `retrieved_on`.**

| doc_id | Lang | Role | Where to get it | State of the lead |
|---|---|---|---|---|
| `moet-tt08-2021` | vi | indexed | National legal database `vbpl.vn` (official copy of Thông tư 08/2021/TT-BGDĐT, Quy chế đào tạo trình độ đại học). Mirror: `daotao.neu.edu.vn` (tier B) | Direct PDF URL in manifest. Text layer looked extractable. Check nothing newer replaced it. |
| `iu-acad-reg-2021` | en | indexed | `cem.hcmiu.edu.vn` — English text of IU Decision 719/QĐ-ĐHQT (6 Dec 2021) | Direct PDF URL in manifest |
| `iu-scse-handbook-2024` | en | indexed | `it.hcmiu.edu.vn` — School of CSE Handbook 2024–2025 | Direct PDF URL in manifest. **Look for a newer edition.** This is your own school: teammates will know real questions about it. |
| `iu-reg-credit-2021-vi` | vi | indexed | Hub page `iem.hcmiu.edu.vn/?p=6640` → "Regulations on university-level training according to the 2021 credit system" | Click through. Verify whether it is the Vietnamese counterpart of Decision 719 |
| `vnuhcm-student-affairs-953-2019` | vi | indexed | Same hub → VNU-HCM Decision 953 (15 Jul 2019) on student affairs | Click through |
| `iu-qd266-scholarship` | vi? | indexed | Same hub → "Regulations on Policies & Scholarships – QD266" | Click through; language/year unverified |
| `iu-qd486-tuition` | vi? | indexed | Same hub → "Regulations on tuition exemption and reduction – QD486" | Click through; language/year unverified |
| `iu-student-rules-2009` | ? | indexed (stale) | Same hub → "International University Student Rules (Updated August 2009)" | Deliberately old → version-conflict questions |
| `hcmut-master-reg-2022` | en | **holdout** | `sim.hcmut.edu.vn/en/?p=11611` — HCMUT Master training regulations (Decision 1216/QĐ-ĐHBK, Apr 2022) | Landing page only |
| `umn-cs-grad-handbook-2023` | en | **holdout** | `cse.umn.edu/cs/graduate-handbook` — page archives one handbook per year | Pick the 2023–24 PDF |

Other things worth knowing from the search:
- The 2017 ISE master's handbook at `iem.hcmiu.edu.vn` says of itself that it does not override the IU Bulletin. It is an obvious v1 "stale document" candidate (English, 60+ pages, includes a VNU-HCM postgraduate regulation appendix).
- The HCMIU physics department hosts a 2024 Module Handbook page (`physics.hcmiu.edu.vn/?p=5119`); the VNU International School (VNU Hanoi) and HCMUT also publish handbooks. Good v1 material.

## 3. Collection procedure (per document, ~5 min)
1. Download the **original file** from the issuing site. No "Print to PDF" from a browser, no Google-Docs re-exports, no screenshots.
2. Save as `data/raw/<doc_id>.<ext>` — the name must equal `doc_id` in the manifest.
3. Open it. Press Ctrl+F and search for a Vietnamese word with diacritics you can see (e.g. `Điều`, `sinh viên`). If nothing is found although the word is visible → scanned pages or legacy-font PDF. Note `has_text_layer=no|partial`. Do not use it in v0.
4. Fill the manifest row (fields below). Compute `sha256_raw` (`sha256sum data/raw/<file>` on Linux/macOS or `Get-FileHash` on Windows).
5. Run `python scripts/extract_text.py <doc_id>`. Read the warning column:
   - very few chars per page → scanned PDF
   - replacement characters (U+FFFD) or a high non-letter ratio → encoding problem (common with old Vietnamese fonts such as TCVN3/VNI)
   - `vi_diacritic_ratio` close to 0 for a Vietnamese document → garbled or wrongly extracted
6. Copy `text_sha256` from `data/processed/<doc_id>.pages.json` into the manifest.
7. Search the text once (`python -m eval.testset grep "<phrase>"`) to make sure the canonical text really contains what the PDF shows.

Known extractor limits in v0 (they are ingestion work, not annotation work): repeated headers/footers stay in the text; tables come out as flowing text; DOCX has no page numbers.

## 4. Manifest format (`data/manifest.csv`, UTF-8)
| Column | Meaning / allowed values |
|---|---|
| `doc_id` | Unique slug: `[a-z0-9-]`, `<publisher>-<short-name>-<year>`. **Never rename after questions exist.** |
| `title` | Official title in its own language |
| `publisher` | Issuing body |
| `doc_type` | `regulation`, `handbook`, `faq`, `procedure`, `circular`, `other` |
| `lang` | `vi`, `en`, `mixed` |
| `doc_version` | Edition label (`2024-2025`, `2021-03-18`). Bump when the text is re-extracted or a new edition replaces it |
| `publication_date`, `effective_date` | ISO date or year, whatever the document states |
| `source_url` | Direct file URL (URL-encode spaces and non-ASCII) |
| `landing_url` | Page the file is linked from, if there is no direct URL |
| `retrieved_on` | Date you downloaded it (`YYYY-MM-DD`) |
| `file_format` | `pdf`, `docx`, `html` |
| `n_pages`, `has_text_layer` (`yes/no/partial`), `has_tables` (`yes/no`) | From step 3/5 |
| `provenance_tier` | `A` published by the institution · `B` official mirror · `C` third party |
| `license_note` | Anything stated about reuse; else "unspecified – local research use" |
| `role` | `indexed`, `holdout`, `excluded` |
| `version_group` | Same document family across years/languages (e.g. `iu-undergrad-regulation`) |
| `doc_status` | `current`, `superseded`, `unknown` |
| `status_checked_on` | Date you checked whether a newer edition exists |
| `sha256_raw`, `sha256_text` | Hash of the downloaded file / of the canonical text |
| `owner` | Teammate responsible for this document |
| `notes` | Anything odd (scanned pages, tables, machine-translated, etc.) |

The eval tooling refuses a test question whose evidence cites a `holdout` document as retrieval evidence, or whose `doc_id` is not in the manifest.

## 5. Growing to ~25 documents (v1, weeks 2–3)
Target mix: ~10 Vietnamese, ~10 English, ~3 mixed/other, 2–3 messy documents (tables, scanned pages), 2 version pairs.

Where to look (search on the official domain only):
- **Vietnamese:** other VNU-HCM member schools (HCMUT, UIT, HCMUS, USSH, UEL) → `sổ tay sinh viên`, `quy chế đào tạo`, `quy định học vụ`; `vnuhcm.edu.vn` → university-wide regulations; Ministry of Education circulars on student affairs, scholarships, tuition.
- **English:** more HCMIU units (Bulletin, School/Department handbooks, exchange/study-abroad guides, Office of Academic Affairs FAQs); international universities' undergraduate handbooks (search `"<university> undergraduate student handbook" pdf` on the official domain).
- **FAQ / procedure pages:** save as PDF from the site with the URL recorded in `landing_url` (`file_format=html` in the manifest).
- **Version pairs:** university sites that archive one handbook per year (UMN does) are ideal — two adjacent years of the same handbook.

Reject a candidate if: no text layer, under ~5 pages of real content, a third-party summary, undated with no publisher, or a duplicate of a document you already have.

## 6. Done checklist
- [ ] Every downloaded file is named `<doc_id>.<ext>` and appears in the manifest
- [ ] All manifest fields filled, or `unknown` with an explanation in `notes`
- [ ] `extract_text.py` output reviewed; no unexplained warnings
- [ ] At least 2 documents each in Vietnamese and English; at least 1 version pair; 2 hold-outs
