# TODO

## Done

### Core platform
- [x] FastAPI app skeleton with layered modules (router / service / repository / models)
- [x] SQLAlchemy 2.0 + Alembic migrations
- [x] Multi-tenant data model — `pg_id` FK on every non-owner table, tenant-scoped repositories
- [x] Request-ID middleware + centralised error handlers
- [x] Pytest suite with in-memory SQLite, fakes for AI / WhatsApp providers
- [x] Test suite green on Python 3.13

### Auth
- [x] PG-owner registration, JWT login, `PATCH /auth/me` profile (incl. UPI VPA)
- [x] `get_current_owner` / `get_tenant` dependencies; tenant identity derived from JWT only
- [x] Bearer auth via token only

### Domain modules
- [x] Properties — rooms CRUD with dynamic `available_capacity`
- [x] Residents — CRUD, capacity guard, move-out flow, ID-OCR onboarding
- [x] Finance — ledger, monthly invoice generation, payments, UPI deep links
- [x] Complaints — AI-parsed list / get / resolve
- [x] Notices — broadcast announcements with delivery audit
- [x] Meals — daily dinner-poll, AI-parsed replies, headcount dashboard
- [x] Inbound webhook + dispatcher (complaints vs. meals routing)

### Integrations
- [x] `AIProvider` Protocol + Gemini implementation + factory
- [x] `WhatsAppClient` Protocol + Meta implementation + factory
- [x] Idempotent webhook handling via unique `provider_message_id` index
- [x] Webhook returns 200 OK fast; heavy work offloaded to `BackgroundTasks`

### Workers
- [x] Celery app + beat schedule
- [x] Pure job functions in `workers/jobs.py` (broker-free unit tests)

### DX / ops
- [x] VS Code debug config (`.vscode/launch.json`) for uvicorn + pytest breakpoints
- [x] Map `AIUnavailableError` → HTTP 503 globally (was leaking as 500 from dependency resolution)
- [x] Make Gemini model configurable via `GEMINI_MODEL`; default bumped from retired `gemini-1.5-flash` to `gemini-2.5-flash`
- [x] GitHub Actions CI — `ruff check` + `pytest` on push / PR (`.github/workflows/ci.yml`)

## Pending

- [x] Add `LICENSE` at project root
- [x] Add `Dockerfile` (multi-stage, slim base) so the API can be containerised and pushed to `ghcr.io` for deployment
