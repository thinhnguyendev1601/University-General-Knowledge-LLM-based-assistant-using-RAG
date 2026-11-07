# RAG API and frontend wiring (prototype, 2026-10-21; real LLM tested 2026-11-06)

How the React chat talks to the RAG core, how to run it locally, and what is left for the
frontend and backend leads.

## Run it (three terminals, from the repo root)

```bash
# 1. local LLM (once: install Ollama, then `ollama pull llama3.2`)
ollama serve

# 2. RAG API - first start loads bge-m3 (~20 s); embeddings are cached in data/index/
uvicorn api.app:app --port 8000
#    RAG_LLM=none uvicorn api.app:app --port 8000   -> retrieval only, no Ollama needed
#    RAG_LLM_MODEL=qwen2.5:3b uvicorn ...           -> any other pulled Ollama model

# 3. frontend - Vite proxies /api/* to :8000
cd projectsoftwareengineeringfrontend && npm ci && npm run dev
#    VITE_USE_MOCK_CHAT=true npm run dev            -> old mock replies, no backend needed
```

Check: `curl localhost:8000/api/health`.

Tests: `pytest` (offline, < 2 s; the live tests skip themselves) and
`RAG_LIVE=1 pytest tests/test_live_llm.py` (real bge-m3 + Ollama, ~40 s). Needs `data/processed/`
locally - it is gitignored, so get the extracted text from Tommy or run `scripts/extract_text.py`.

## What the real LLM does today (llama3.2 3B, dev split, 2026-11-06)

`python -m eval.run_eval --config eval/configs/03c_dense_struct_llama32.yaml` - same numbers on two
consecutive runs. Only 10 dev questions (7 answerable), so these are early indications.

| | value |
|---|---|
| unanswerable / adversarial refused | 3 / 3 (refusal F1 1.0, unsupported_answer_rate 0.0) |
| answerable questions answered (false_refusal_rate) | 7 / 7 (0.0) |
| answerable questions answered **correctly** (read by hand) | 4 / 7 |
| cited quotes found verbatim in the cited chunk | 100 % |
| latency per answer | mean 7.3 s, p95 11.6 s (CPU) |

The 3 wrong answers are confident and cited: TM-007 and TM-008 because retrieval never finds the
right passage (known, not in the top 10), TM-006 a reasoning error. `unsupported_answer_rate` only
counts unanswerable questions, so it does **not** catch these - next steps are hybrid search +
reranker for retrieval and a faithfulness check (CLAUDE.md §7 layer 4).

Fixes that got there (all in `rag/pipeline.py`, each with a unit test): citations come **before** the
answer in the JSON schema (evidence first; this alone took false refusals from 0.71 to 0); a
verbatim quote labelled with the wrong `[C#]` is relinked to the source that holds it; an answer
that is only source ids, or says "no information" in prose, is a refusal; JSON inside the answer is
flattened; snapped quotes are widened to whole words; superseded documents are marked in the prompt.

## Endpoints

### `POST /api/chat/messages`
Request (the UI's existing contract, plus one optional field):
```json
{ "conversationId": "c1", "content": "Ở UIT khi nào bị cảnh báo học tập?", "institutionId": "uit" }
```
`institutionId` comes from a school picker. Leave it out and the backend detects the school
in the question (names, abbreviations, Vietnamese names, missing diacritics, typos in long
names): `rag/institutions.py`.

Response = the UI's `ChatMessage` plus optional extras (`types/chat.ts`):
```json
{
  "id": "…", "conversationId": "c1", "role": "assistant", "createdAt": "…",
  "content": "answer text\n\nNguồn / Sources:\n[1] Quy chế … — Điều 9 — tr. 7\n    “verbatim quote”",
  "status": "answered | refused",
  "answer": "answer text only",
  "citations": [{ "chunkId", "docId", "title", "sourceUrl", "section", "page", "quote" }],
  "refusalReason": "institution_not_covered | low_retrieval_score | model_abstained | unverified_citation | invalid_model_output | null",
  "institution": { "ids": ["uit"], "source": "user | detected | none" },
  "latencyMs": 41234
}
```
`content` already contains the sources as plain text, so the current chat UI shows citations
with **no component change**. `citations[]` is there for a proper source panel.

Errors use the UI's `{ "message": … }` shape: `400` unknown `institutionId`, `503` Ollama not
running / model not pulled (the UI's "Thử lại" button covers both).

### `GET /api/institutions`
`[{ "id": "iu", "name_en": "…", "name_vi": "…", "covered": true }, …]` - for the school
picker. `covered: false` schools (HCMUT, MIT, …) are known names with no indexed documents;
questions about them are refused with `institution_not_covered` before any LLM call.

### `GET /api/health`
Chunk count, embedder, LLM and pipeline config id.

## Frontend changes made (services + types only, per the frontend CLAUDE.md)
- `services/chat.ts`: `sendMessage` calls the API (optional 3rd arg `institutionId`);
  `getInstitutions()` added. Conversations stay local (mock) - no backend endpoint yet.
- `services/httpClient.ts`: per-request timeout; chat uses 180 s (`VITE_CHAT_TIMEOUT_MS`),
  everything else keeps 15 s. A CPU LLM takes 30-120 s per answer.
- `types/chat.ts`: optional `status`, `citations`, `refusalReason`, `institution`; `Institution`.
- `vite.config.ts`: dev proxy `/api` → `http://localhost:8000`.
- Verified: typecheck, lint, prettier, 56/56 vitest.

## Left for the frontend lead
1. **School picker** above the chat input: `getInstitutions()`, pass the chosen id as the 3rd
   argument of `sendMessage`. Grey out `covered: false` schools.
2. **Source panel** rendering `message.citations` (title, section, page, quote, `sourceUrl`
   link) instead of relying on the plain-text block in `content`.
3. **Refused answers** styled differently (`status === 'refused'`), optionally showing why.
4. Typing indicator copy: answers take up to ~2 minutes on CPU.

## Left for the backend lead - how to plug the RAG core into the real backend

The only contract is one call (do not reimplement retrieval or prompts in the backend):

```python
from rag.pipeline import DensePipeline
pipe = DensePipeline(llm="ollama", llm_model="llama3.2")   # once at startup: ~20 s, ~2 GB RAM
r = pipe.answer("question text", institution="iu" | None)  # -> core.schemas.AnswerResult
# r.status "answered" | "refused", r.answer, r.citations[{chunk_id, quote}], r.refusal_reason,
# r.retrieved (top-10 ScoredChunk), r.latency_ms, r.trace["institution"]
pipe.institution_options()                                 # school picker list
```

Rules that keep it working:
1. **Create the pipeline once** (app startup / lifespan), never per request - it loads bge-m3.
2. **Serialise LLM calls** (`api/app.py` uses a lock). Ollama on CPU handles one answer at a time;
   run `answer()` in a worker thread (FastAPI sync `def` route does this) so the event loop stays free.
3. **Keep the response shape** of `POST /api/chat/messages` (above) - the React app already
   consumes it. Easiest path: move the three routes from `api/app.py` into your app, add auth as a
   dependency, and save the user message + returned assistant message to the conversation tables.
4. Map errors as now: `ValueError` -> 400 (unknown school), `RuntimeError` -> 503 (Ollama down).
5. Store `status`, `refusalReason`, `citations` and `latencyMs` with each assistant message -
   the feedback button and admin dashboard need them, and "incorrect answer" reports become
   regression questions (CLAUDE.md §7 layer 7).
6. Upload/ingestion later: a new document must get a manifest row with `role=indexed`, then its
   canonical text in `data/processed/`; the index re-embeds automatically (cache key = content).

Still to build on the backend side: auth/JWT, Postgres, conversation storage
(`GET/DELETE /api/chat/conversations…`), feedback, logging, document upload, and moving the
in-memory index to pgvector behind the same `retrieve()` call.
