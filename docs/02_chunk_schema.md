# Chunk schema and the canonical-text contract

Code: `core/schemas.py` (models) and `core/textnorm.py` (normalisation). This page explains *why* the schema looks the way it does and what the ingestion owner must guarantee so that evaluation keeps working while chunking, embedding and retrieval change every week.

## 1. The one idea everything depends on
```
raw file ──extract──▶ CANONICAL TEXT  (data/processed/<doc_id>.txt, NFC-normalised, frozen per doc_version)
                          │
                          ├── chunker  → Chunk(char_start, char_end, text = canonical[start:end], section_path, page…)
                          └── test set → evidence QUOTES (verbatim strings) → resolved to spans at build time
```
- **Offsets point into the canonical text, never into the PDF.** A chunk and a gold evidence span can be compared by pure interval arithmetic, whatever chunker produced the chunk.
- **The test set stores quotes, not chunk IDs.** Chunk IDs change with every chunking experiment; quotes don't. `python -m eval.testset build` re-resolves quotes to offsets every time, so ablations on chunking need no relabelling.
- **Text is normalised once** (`normalize_text`: NFC, non-breaking/zero-width characters removed, whitespace collapsed, soft-hyphen line breaks joined). Vietnamese text extracted from PDFs often arrives decomposed (NFD): without this step the same phrase can compare unequal.
- **Canonical text is frozen.** If you improve the parser, bump `doc_version` in the manifest and re-run `eval.testset build`; questions whose quotes no longer resolve are reported as errors and get fixed by hand. Do not silently re-extract.

## 2. `Chunk` fields
| Field | Type | Rule |
|---|---|---|
| `chunk_id` | str | `make_chunk_id(doc_id, char_start, char_end)` → `"<doc_id>:<start>:<end>"`. Deterministic; validated by the model |
| `doc_id` | str | Must exist in the manifest |
| `doc_version` | str | Copied from the manifest |
| `text` | str | **Exactly** `canonical[char_start:char_end]`. Call `verify_chunk(chunk, canonical)` in ingestion tests for every chunk |
| `char_start`, `char_end` | int | Half-open interval in canonical text |
| `page_start`, `page_end` | int \| None | 1-based, from `<doc_id>.pages.json` (`page_starts`). `None` for DOCX/HTML |
| `section_path` | list[str] | Heading trail, e.g. `["Chương II", "Điều 12. Cảnh báo học vụ"]`. Used for display, citation labels and the embedding header |
| `lang` | `vi`/`en`/`mixed` | Document language from the manifest; for `mixed` documents detect per chunk |
| `chunk_type` | enum | `paragraph`, `list`, `table`, `heading`, `other` |
| `token_count` | int \| None | Tokens under the embedding model's tokenizer |
| `chunker` | str | Recipe label incl. parameters, e.g. `struct-v1;max=450;overlap=50` |

`Chunk.embedding_text()` returns `"<section_path joined by ' > '>\n<text>"` — the contextual header goes into the *embedding* but never into the stored `text`, so the invariant above still holds.

## 3. Chunking policy v1 (spec for the ingestion owner)
1. **Split on document structure first, size second.**
   - Vietnamese regulations: `Chương` → `Mục` → `Điều` → `Khoản` (`1.`, `2.`) → `Điểm` (`a)`, `b)`).
   - English documents: `Chapter/Part/Section/Article`, numbered headings (`3.2 …`), bullet lists.
   - One `Điều`/section is the default unit. If it exceeds the size cap, split at `Khoản`/paragraph boundaries and repeat the article heading in `section_path`.
2. **Size:** target ~250–450 tokens, hard cap ~600. Merge tiny neighbouring sections up to the target. Overlap (~15%) only *inside* a split long section, never across articles.
3. **Never split** a table row, a numbered list item, or a heading from its first paragraph. Tables: one chunk per table if it fits, else split by rows and keep the header row in every part.
4. **Never cross document boundaries.**
5. Record `chunker` so a result can always be traced back to its recipe.
6. Fixed-size chunking (e.g. 500 tokens, 50 overlap) is kept as the **ablation baseline**, not the default.

Regex starting points (test on real files, they will need tuning):
```python
CHUONG = r"^(CHƯƠNG|Chương)\s+([IVXLC]+|\d+)\b"
DIEU   = r"^(Điều|ĐIỀU)\s+\d+[a-z]?\."
KHOAN  = r"^\d+\.\s"
DIEM   = r"^[a-zđ]\)\s"
EN_HEAD = r"^(Article|Section|Chapter|Part)\s+[\dIVX]+\b|^\d+(\.\d+)*\s+[A-Z]"
```

## 4. What defines an "index" (so results stay comparable)
An index = (manifest hash of `role=indexed` docs) + (chunker recipe) + (embedding model + version) + (sparse/BM25 tokenizer). Store it as `index_id` and copy it into `AnswerResult.config_id`; the eval run then records exactly which index produced each number. Rebuilding an index must never overwrite an old one that a saved eval run refers to.

## 5. Suggested Postgres / pgvector shape (for whoever writes the migration)
```sql
documents(doc_id PK, title, lang, doc_version, role, doc_status, sha256_text, ...)      -- mirrors the manifest
chunks(index_id, chunk_id, doc_id FK, char_start, char_end, page_start, page_end,
       section_path jsonb, lang, chunk_type, text, embedding vector(1024), token_count,
       PRIMARY KEY (index_id, chunk_id))
-- 1024 = bge-m3 dense size; change with the model. Add HNSW index on embedding, GIN on a tsvector/BM25 column.
feedback(id, user_id, query, answer_id, retrieved_chunk_ids, verdict, comment, created_at)
```
Filtering by `role='indexed'` must happen in the query — holdout documents must be impossible to retrieve.

## 6. Contract the pipeline owes evaluation
`answer(query) -> AnswerResult`:
- `retrieved`: the chunks the generator actually saw, ranked from 1, with the score of the *final* stage.
- `citations`: each `chunk_id` must be in `retrieved`; each `quote` must be a verbatim substring of that chunk (checked by `quote_verified_rate`).
- `status`: `"refused"` only when the system deliberately declines; `refusal_reason` from a fixed vocabulary (`low_retrieval_score`, `model_abstained`, `unverified_citation`, `faithfulness_failed`, …).
- `trace`: gate values, judge output, timings — free-form, but keep the keys stable so error analysis can slice on them.
- Exceptions are allowed to escape: the harness catches them and counts the question as failed.

## 7. Invariant tests to add on day one (ingestion owner)
```python
def test_chunks_reproduce_canonical_text(doc_id):
    canon = Path(f"data/processed/{doc_id}.txt").read_text(encoding="utf-8")
    for c in chunk_document(doc_id):
        verify_chunk(c, canon)          # text == canonical[start:end]
def test_no_chunk_crosses_documents_or_leaves_bounds(): ...
def test_holdout_docs_never_indexed(): ...
```
