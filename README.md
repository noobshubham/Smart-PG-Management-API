# Smart PG Management API

![ci](https://github.com/noobshubham/Smart-PG-Management-API/actions/workflows/ci.yml/badge.svg)

Multi-tenant SaaS backend for Paying Guest property owners. Built with FastAPI,
SQLAlchemy 2.0, Pydantic v2, Celery, Gemini, and the WhatsApp Business API.

## Architecture

```
app/
  core/             # config, db, security, shared deps, middleware, errors
  modules/          # one folder per bounded context — see layering below
    auth/           # PG owner registration, JWT login, profile (incl. UPI VPA)
    properties/     # rooms — CRUD + dynamic available_capacity
    residents/      # resident CRUD, capacity guard, move-out, ID-OCR onboarding
    finance/        # ledger, monthly invoice generation, payments, UPI links
    complaints/     # AI-parsed complaints (list / get / resolve)
    notices/        # broadcast announcements with delivery audit
    inbound/        # WhatsApp webhook + dispatcher (complaints vs. meals)
    meals/          # daily dinner-poll, AI-parsed replies, headcount dashboard
  integrations/
    ai/             # AIProvider Protocol + Gemini impl + factory
    whatsapp/       # WhatsAppClient Protocol + Meta impl + factory
  workers/          # Celery app + beat schedule + system-level jobs
migrations/         # Alembic
tests/              # pytest, in-memory SQLite, fake AI/WhatsApp
```

Each `modules/<name>/` folder follows the same layered pattern:

```
router.py      # HTTP layer — FastAPI route handlers
schemas.py     # Pydantic request / response models
service.py     # business rules — pure Python, no FastAPI / SQL imports
repository.py  # data access — SQLAlchemy queries only
models.py      # ORM tables
exceptions.py  # domain errors, mapped to HTTP in the router
```

## Architectural invariants

1. **Multi-tenancy.** Every non-owner table has a `pg_id` FK. Every repository
   method takes `pg_id` as its first argument. The only authorised
   tenant-boundary crossings are explicitly suffixed `_global` (e.g.
   `find_active_by_phone_global`) and live solely in the inbound webhook and
   the worker jobs.

2. **Tenant identity comes from the token.** `app.core.deps.get_tenant`
   derives `pg_id` from the JWT subject — never from request body or query
   string.

3. **Provider-agnostic integrations.** `AIProvider` and `WhatsAppClient` are
   `typing.Protocol`s. Domain code never imports Gemini or Meta directly.
   Swapping vendors is one new impl plus a factory branch.

4. **Webhook returns 200 OK fast.** All heavy work (AI calls, DB writes,
   outbound sends) is offloaded to FastAPI `BackgroundTasks` so providers
   don't retry. Idempotency is enforced via a unique index on
   `complaints.provider_message_id`.

5. **AI failures never lose data.** If Gemini fails, the inbound message is
   still persisted with `needs_review=True`. Owners see it in the dashboard
   and can categorise manually.

6. **Pure jobs.** Celery tasks (`workers/tasks.py`) are thin wrappers; the
   actual logic is plain functions in `workers/jobs.py` taking
   `(db, whatsapp, ...)`. Fully unit-testable without a broker.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit secrets

alembic revision --autogenerate -m "init"
alembic upgrade head

uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive Swagger UI.

### Background workers

```bash
# Worker: executes tasks
celery -A app.workers.celery_app worker --loglevel=info

# Beat: emits scheduled triggers (daily meal poll, monthly rent reminders)
celery -A app.workers.celery_app beat --loglevel=info
```

Both read `CELERY_BROKER_URL` from `.env`. In production run them as
separate services; in dev a single Redis instance is enough.

### Tests

```bash
pytest
```

Tests use an in-memory SQLite, override `get_db`, `get_ai_provider`, and
`get_whatsapp_client` with fakes from `tests/fakes.py`, and never touch the
production engine, Redis, Gemini, or Meta.

## API quickstart

```bash
# Register + login
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"pg_name":"Sunrise","owner_name":"A","phone_number":"919000000001","password":"supersecret"}'

TOKEN=$(curl -sX POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"phone_number":"919000000001","password":"supersecret"}' | jq -r .access_token)

# Set the UPI VPA so payment links can be generated
curl -X PATCH localhost:8000/auth/me -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"upi_vpa":"sunrise@upi"}'

# Create a room and a resident
curl -X POST localhost:8000/rooms -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"room_number":"101","total_capacity":3}'

# Generate this month's invoices
curl -X POST localhost:8000/finance/invoices/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"month_year":"2026-05"}'

# Get a UPI deep link for a ledger entry
curl -H "Authorization: Bearer $TOKEN" \
  localhost:8000/finance/ledger/1/upi-link
```

## Observability

Every response carries an `X-Request-Id` header (taken from the inbound header
if present, otherwise generated). The id is attached to `request.state` and
included in 5xx error bodies, so a user-reported failure can be grepped
directly in logs.
