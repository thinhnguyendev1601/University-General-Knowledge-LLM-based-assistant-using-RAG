# Changes Since the Original Prototype

- **Real accounts:** added registration, login, session restoration, logout, and password reset using FastAPI/PostgreSQL.
- **Registration policy:** accept only `@university.edu.vn` and activate accounts immediately without email verification.
- **Account security:** added Argon2id password hashing, HttpOnly session cookies, CSRF/Origin checks, session expiry/revocation, and rate limits.
- **Redis session cache:** added expiring session snapshots, invalidation on logout/password reset, and DB fallback during Redis outages; PostgreSQL still enforces session validity and user permissions.
- **Persistent database:** added SQLAlchemy models and Alembic migrations for accounts, sessions, conversations, document metadata, versions, and audit records.
- **Server-side history:** added conversation creation, listing, renaming, deletion, message pagination, and saved answers/citations, with ownership checks.
- **Reliable retry:** added `requestId`, processing states, duplicate-free replay, recovery after interruption, and rejection of late results.
- **Frontend integration:** connected the main React frontend to real account/history APIs; reload and login restore PostgreSQL history instead of storing new chats in localStorage.
- **Document metadata administration:** added repeatable manifest import, admin list/detail/update/version APIs, filters, pagination, and transactional audit records.
- **RAG processing control:** added a bounded queue, queue/processing deadlines, overload responses, retry guidance, and timing measurements within one API process.
- **Operations and testing:** added live/ready probes, request-correlated logs, demo seeding, maintenance, SMTP checks, backup/restore, an Nginx template, and regression/integration tests.

The existing BGE-M3/Ollama pipeline, corpus, and vector cache were retained.
Admin UI integration, file upload/ingestion, index publication, answer caching,
multi-turn model context, streaming, and multi-process coordination remain unfinished
or outside scope. External SMTP and real domain/TLS deployment are not included.
