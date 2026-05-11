# LinkUp Backend

FastAPI application: auth, rides, bookings, notifications, chat, workers.

## Running locally (development)

- **Windows**: `run-backend.bat` — stops any process on port 8000, then runs `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Linux / macOS**: `./run-backend.sh` (make executable first: `chmod +x run-backend.sh`)

For production, use Docker (see root `docker-compose.yml`).

- **Dockerfile (multi-stage):** `builder` stage installs gcc + libpq-dev + uv and Python dependencies. `runtime` stage is a clean `python:3.11-slim` with only `libpq5` (no build tools) — copies site-packages from builder. `development` inherits builder (for gcc rebuilds); `migrate`, `worker`, `production` inherit runtime (slim, non-root `appuser`). Production images do not contain gcc, test files, or pyproject.toml.
- **Production DEBUG guard:** `app/main.py` raises `RuntimeError` at import time if `settings.ENVIRONMENT == "production"` and `DEBUG=True` — the process crashes before serving any request, preventing accidental debug mode in production.
- **Uvicorn workers (Docker):** `backend/entrypoint.sh` מריץ `uvicorn ... --workers` לפי **`UVICORN_WORKERS`** ב-`backend/.env` (ברירת מחדל 1). ב-`.env.example`: **`UVICORN_WORKERS=4`**. פיתוח לוקאלי בלי דוקר: `run-backend.sh` / `run-backend.bat` — `--reload`, worker אחד.
- **WebSocket auth:** `get_current_user_ws` מאמת **JWT בלבד** (אובייקט `WsUser`), בלי `SELECT` ל-DB בזמן חיבור — ראו `app/api/dependencies/auth.py`. HTTP endpoints עם `get_current_user` עדיין טוענים משתמש מ-DB.

**Push (FCM):** בפרודקשן (Model B) הגדר `FIREBASE_CREDENTIALS_JSON` ב־`backend/.env` (JSON בשורה אחת, ללא file mount). `FIREBASE_SERVICE_ACCOUNT_PATH` נשאר fallback לפיתוח מקומי בלבד — פירוט ב־`docs/FCM_SYSTEM_SUMMARY.md` וב־README בשורש.

## Email rendering architecture

- Email HTML rendering now runs through a dedicated **Node.js + Express + React Email** service in `../email-renderer/`.
- Backend/notification-worker call [`app/domain/notifications/channels/email/renderer.py`](app/domain/notifications/channels/email/renderer.py), which delegates to:
  - `POST {EMAIL_RENDERER_URL}/render` with `{ template, props }`
- Configure endpoint in `backend/.env`:
  - `EMAIL_RENDERER_URL=http://email-renderer:3001`
- Template names are mapped in [`app/domain/notifications/config/templates_map/email_conf.py`](app/domain/notifications/config/templates_map/email_conf.py) as **PascalCase** registry keys (not Jinja paths).
- Compose runtime expects `email-renderer` healthy before `backend`/`notification-worker` start.

## Environment

Copy `.env.example` to `.env` and set your values. See root README for full setup.

**Groq (optional):** for chat summaries (`ai-worker`) and passenger AI ride search parsing, set **`GROQ_API_KEY`** or **`GROK_API_KEY`** in `backend/.env` (see `app/domain/chat/ai/client.py`). Docker Compose already loads `backend/.env` into the backend and worker containers — no duplicate key in `docker-compose.yml`.
The same parser endpoint (`POST /api/v1/passenger/passengers/ai-parse-search`) is shared by both passenger search and driver CreateRide in the frontend; business rule differences are enforced client-side per flow.

**`GET /api/v1/passenger/passengers/search-rides`** supports optional **`departure_date`** (Jerusalem calendar day bounds in UTC), **`departure_time`** (±2h window), or **`departure_time` + `departure_time_to`** (closed range); mixing date with timestamps returns **422**. Pagination cursor is **opaque** (`after`/`next_cursor`) via shared helper (`app/core/pagination/cursor.py`), and destination filtering supports optional **`destination_radius`** (km) in addition to `search_radius` — see **`docs/architecture/API.md`** and **`app/domain/passengers/schema.py`** (`RideSearchRequest`).

**Database connection pool** (optional tuning): `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`. **`DB_STATEMENT_TIMEOUT_MS`** is applied **per session** via SQLAlchemy `connect_args` → asyncpg `server_settings` in [`app/db/session.py`](app/db/session.py) (default 30000ms; set in `.env`/`.env.example`). Alembic **017** also sets a fixed role-level **ceiling of 60000ms** as defense-in-depth — gate of last resort if `connect_args` ever bypasses (e.g., direct connection without the engine). Documented in `.env.example` and `docs/architecture/DEVELOPMENT.md`.

**Migrations:** after pulling, run **`uv run alembic upgrade head`**. Revision **`019_booking_lifecycle_enum`** extends PostgreSQL **`booking_status`** with **`en_route`**, **`arrived`**, **`trip_in_progress`** (required for passenger-request bulk cancel and active-booking filters). See **`docs/architecture/DATABASE.md`**.

## Security & auth (backend)

- **Password hashing:** bcrypt (passlib); `get_password_hash` / `verify_password` are **async** and offload CPU work via `asyncio.get_running_loop().run_in_executor` so the ASGI event loop stays responsive under load.
- **Rate limiting:** Redis-backed limiter on **`POST /api/v1/auth/register`** and other sensitive auth routes (see `app/api/dependencies/rate_limit.py`); window/size from `RATE_LIMIT_AUTH_*` in config.
- **Username enumeration (OWASP):** `authenticate_and_create_token` raises the same **`InvalidCredentialsError`** (401) for unknown email and wrong password so clients cannot infer whether an account exists. Covered in `tests/test_auth.py` (with `DATABASE_URL`).
- **Email / reset OTP:** `VerificationService` uses **`secrets`** for codes, **`hmac.compare_digest`** for comparison, Redis-backed **attempt counter** (brute-force guard), counter **reset** when a new OTP is issued — see `app/domain/auth/verification_service.py`.
- **Chat message idempotency:** optional **`Idempotency-Key`** on **`POST …/chat/conversations/{conversation_id}/messages`** — דפוס מקביל ל־§19 עם מפתח `idempotency:chat_message:{user_id}:{key}` וקוד תחת **`app/domain/chat/message_idempotency.py`**. פירוט: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §25**.

Portfolio-style summary: **`docs/ENGINEERING_HIGHLIGHTS.md`**.

## Billing (Stripe)

סיכום מלא של ה-refactor (לפני/אחרי, webhooks, reconciler, השוואת Kafka): **`../docs/BILLING_REFACTOR_SUMMARY.md`**.

- **Checkout idempotency:** כותרת אופציונלית **`X-Idempotency-Key`** על **`POST /api/v1/billing/checkout`** — שמירה בטבלת **`idempotency_keys`** (ראו **`app/domain/billing/idempotency.py`**, מיגרציה רוויזיה **`015_billing_idem`**).
- **Reconciler:** **`BillingReconciler`** מתוזמן מ־**`app/core/lifespan.py`** (APScheduler) כש־**`BILLING_RECONCILER_ENABLED`**; נעילת Postgres consultative, סנכרון תשלומים **`pending`** מול Stripe (**`reconciler.py`**).
- **בדיקות יחידה (ללא DB חובה לחלקן):** **`tests/domain/test_billing_state_machine.py`**, **`tests/domain/test_billing_reconciler.py`** — מומלץ **`uv run pytest`** מתוך **`backend/`** עם venv הפרויקט.
- **Alembic:** אחרי **014** שני צעדי **015** מתמזגים ב־**`016_merge015_heads`**; פירוט **`docs/architecture/DATABASE.md`**.

## Tests & CI (quality)

- **pytest:** מתוך `backend/` — **`make test`** מריץ קודם **`uv run alembic upgrade head`** ואז **`uv run pytest`** (זהה לסדר ב־CI). לחלופין: **`uv run pytest tests/ -v`** אחרי מיגרציה ידנית. טסטי אינטגרציה עם DB דורשים **PostgreSQL + PostGIS** וסכמה מ־Alembic. ב־`tests/conftest.py` מקור ה-DSN: **`DATABASE_URL`** (עדיפות), או **`TEST_DATABASE_URL`** (תאימות לאחור), או ברירת מחדל ל-docker-compose המקומי.
- **GitHub Actions** (`.github/workflows/backend-ci.yml`): שירות Postgres, **`DATABASE_URL` ברמת ה-job** (מיפוי אחיד ל־**Alembic** ול־**pytest**), שלבי איכות בסדר בפועל: **Ruff check** → **Ruff format --check** → **`uv run alembic upgrade head`** → **`uv run pytest`**. קבצים תחת `alembic/` נכללים ב־autogenerate דרך `env.py` (ייבוא `app.db.models`); אם CI ירחיב ל־`ruff check alembic/`, ה־`per-file-ignores` ל־`alembic/env.py` מכסה F401 על ייבוא registry.
- **Settings:** משתני סביבה **`DATABASE_URL`** / **`REDIS_URL`** נקראים ל־`DATABASE_URL_RAW` / `REDIS_URL_RAW` דרך **`validation_alias=AliasChoices(...)`** ב־`app/core/config.py` (pydantic-settings) — כך Alembic (`settings.DATABASE_URL`) והריצה ב-CI מסתנכרנים.

## Updating the API contract

מקור האמת לחוזה ה-API הוא **`app.openapi()`** ב-[`app/main.py`](app/main.py). חוזה ה-Orval בפרונט (`frontend/src/api/generated/`) מיוצר אוטומטית מ-FastAPI ו**חייב** להיות מסונכרן בכל PR שמשנה schema/router/Pydantic model.

- **לאחר שינוי endpoint או schema** הריצו בשורש הריפו:
  - `make openapi` — מייצא את הסכמה ל-`frontend/openapi-snapshot.json` (gitignored), מריץ Orval, ומציג את ה-diff ב-`frontend/src/api/generated/`. את התוצרים שם **קמיטו**.
  - או מהפרונט: `npm run openapi:sync` (קורא לאותו target).
- **ה-CI** ([`.github/workflows/openapi-contract.yml`](../.github/workflows/openapi-contract.yml)) מאמת ש-`frontend/src/api/generated/` תואם ל-FastAPI; ללא Postgres/Redis/RabbitMQ בייצוא — `app.openapi()` עצמו lazy ולא נוגע ב-IO.
- **הסקריפט:** [`backend/scripts/export_openapi.py`](scripts/export_openapi.py) (פלט דטרמיניסטי: `indent=2`, `sort_keys=True`, `ensure_ascii=False`).

**Error responses (JSON, `error_code`, `trace_id`, handlers):** [`docs/ERRORS.md`](../docs/ERRORS.md).

**Health & circuit breakers (Google Maps + Brevo email):** `GET /api/v1/health` runs DB, Redis, and RabbitMQ checks; response includes **`status`** (`healthy` if all three are `ok`, else `unhealthy` — **503** in that case) and informational **`circuit_breakers`** (`google_geocoding`, `google_directions`, `google_distance_matrix`, `brevo_email` — values `closed` / `open` / `half_open`). See [`../docs/architecture/API.md`](../docs/architecture/API.md#health), [`../docs/architecture/NOTIFICATIONS.md`](../docs/architecture/NOTIFICATIONS.md), and [`../docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md) §20.

**Logging (structured):** בפרודקשן `LOG_FORMAT=json` עם **structlog** (`JSONRenderer`); בפיתוח `LOG_FORMAT=text` עם `ConsoleRenderer` — ראו `app/core/logging.py` ו־`RequestIDMiddleware` ב־`app/main.py` (מקור אמת: `ARCHITECTURE.md` — Observability).

## Admin API (`/api/v1/admin`)

Endpoints for operators only: FastAPI dependency **`get_current_admin_user`** (`app/api/dependencies/admin.py`) requires `User.is_admin`. Router: **`app/domain/admin/router.py`**, mounted in **`app/api/v1/api_router.py`** with prefix **`/admin`**. Includes stats, health, user list + PATCH (active/admin flag), rides/groups lists and ride cancel, outbox list/detail + requeue for FAILED events, ride/booking lookup; sensitive actions log with **`[admin_audit]`**.  
**Web UI** lives in the main frontend: **`frontend/src/features/admin/`** → routes under **`/admin`** — see root **`ADMIN_DASHBOARD.md`**.

## Bookings — aggregated reads (My Bookings)

- **Service split (SRP):** read-only aggregations live in [`app/domain/bookings/booking_reads_service.py`](app/domain/bookings/booking_reads_service.py) (`BookingReadsService`); GPS broadcast validation lives in [`app/domain/bookings/location_service.py`](app/domain/bookings/location_service.py) (`BookingLocationService`). Lifecycle mutations (`request_to_join`, approve/reject/cancel, etc.) stay in [`app/domain/bookings/service.py`](app/domain/bookings/service.py) (`BookingService`). Both helper modules are also re-exported from `service.py` for backward-compatible imports.
- **`GET /api/v1/bookings/driver-summary/active`** (auth): active rides only (`open` / `full` / `active`), **soft limit 200** — `get_driver_active_rides`; `with_loader_criteria` includes in-trip booking statuses.
- **`GET /api/v1/bookings/driver-summary/history`** (auth): completed/cancelled rides with cursor pagination (`limit`, `after`) — `get_driver_history_rides`; history loader uses **confirmed/cancelled/completed/rejected** so passengers still appear on past rides.
- **`GET /api/v1/bookings/passenger-summary/active`** / **`…/history`**: active (**cap 200**) vs terminal bookings + cursor — `get_passenger_active_bookings` / `get_passenger_history_bookings`.
- **Important semantics:** `/driver-summary/active` and `/passenger-summary/active` are bounded snapshots (soft cap 200), not complete active feeds; very heavy users may not see all active rides/bookings in a single response.
- **Cursors:** [`app/core/pagination/cursor.py`](app/core/pagination/cursor.py) (URL-safe Base64 JSON, timestamps normalized to **UTC**; shared across bookings/chat/rides/passengers).
- **Chat inbox pagination:** `GET /api/v1/chat/conversations` נשען על cursor אטום דרך ה-core helper, עם מיון keyset לפי `COALESCE(conversations.last_message_at, conversations.created_at)`; `last_message_at` נשמר בכתיבה ונעשה לו backfill במיגרציה **020**.
- **Shared manifest mapping:** `booking_to_manifest_item` in [`app/domain/bookings/manifest_mapping.py`](app/domain/bookings/manifest_mapping.py) feeds manifest + summary passengers (via `BookingReadsService`).
- **GPS REST:** `BookingLocationService.broadcast_driver_location` / `broadcast_passenger_location` centralize permission checks; routers delegate only.
- **Frontend contract:** `fetchDriverActive` / `fetchDriverHistory` / `fetchPassengerActive` / `fetchPassengerHistory` in `frontend/src/api/bookings.ts`; React Query keys `qk.bookings.driverActive`, `driverHistory`, `passengerActive`, `passengerHistory`; mapping in `frontend/src/pages/MyBookings/myBookings.mappers.ts`.

See `docs/architecture/API.md` and `docs/architecture/DATABASE.md`.

## Async architecture updates (rides / bookings / passengers)

- Core flows in passenger requests, bookings, and rides were refactored to SQLAlchemy 2.0 async patterns:
  - `AsyncSession` usage in API/service paths
  - `select(...)` + `await db.execute(...)` for async querying
  - `await db.flush()` / `await db.commit()` in async transaction boundaries
- **Transaction ownership (CRUD flush-only):** `CRUDUser` write methods use `db.flush()` only — callers own the transaction with explicit `await db.commit()`. This enables atomic DB writes + outbox events in a single transaction. Session factory uses `expire_on_commit=False`, so no `db.refresh()` is needed after commit. See `docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §29.
- **Bookings are async-only** now (no `db.run_sync`): lock-critical paths use `select(...).with_for_update()` directly on `AsyncSession` to prevent races while keeping the call chain fully async.
- **Workers:** notification handlers (e.g. `notification_tasks.py` — ride created, booking approved, **ride cancelled**) query with `await db.execute(select(...))`; `find_passengers_for_ride_notification` is async. No `db.run_sync` in application code (Alembic `env.py` still uses `connection.run_sync` for migrations).
- Result: lower event-loop blocking risk, cleaner async call chains, and safer concurrency in booking/ride state transitions.

## SQLAlchemy model registry (imports)

- **[`app/api/v1/api_router.py`](app/api/v1/api_router.py)** begins with `import app.db.models` so domain routers load after required ORM models are registered on `Base.metadata` (avoids string-relationship resolution errors and import-order surprises). This registry is intentionally focused on API/domain relationship loading and is not a claim that every ORM class in the repository is re-exported there.
- **[`alembic/env.py`](alembic/env.py)** imports `app.db.models` after `Base` so **`target_metadata`** includes all tables for **`alembic revision --autogenerate`**.
- **`main.py`** may still import `app.db.models` before `api_router` for clarity; duplicate import is harmless.

**Ruff:** side-effect imports are allowed via **`[tool.ruff.lint.per-file-ignores]`** for **`F401`** on `api_router.py`, `app/db/models.py`, and `alembic/env.py` — see [`pyproject.toml`](pyproject.toml).

## Migrations

Alembic lives in `alembic/`.

- **Locally (repo + `uv`):** from **`backend/`** run **`uv run alembic upgrade head`** — same binary resolution as **`make migrate`** / CI.
- **Docker Compose:** the **`migrate`** image uses **`ENTRYPOINT ["alembic"]`**; the service runs **`alembic upgrade head`** once before **backend** and workers (`notification-worker`, `task-worker`, `ai-worker`). The API **Dockerfile** `CMD` does **not** run migrations (`gunicorn` / `uvicorn` only). Off Compose (container image alone or another orchestrator): run migrations as a Job/init step — see **`docs/architecture/DEVELOPMENT.md`**.

Canonical migration table + merge note (**`016_merge015_heads`**, **`015_billing_idem`**): **`docs/architecture/DATABASE.md`**.

## Load testing (k6)

Primary scripts live under **`k6/scripts/`** (Grafana k6), with shared helpers in `k6/lib/`.

- `k6/scripts/load_test_auth.js`
- `k6/scripts/load_test_rides.js`
- `k6/scripts/load_test_users.js`
- `k6/scripts/load_test_groups.js`
- `k6/scripts/load_test_chat.js`
- `k6/scripts/load_test_geo.js`
- `k6/scripts/load_test_ws.js`

Legacy wrappers kept for compatibility:
- `load_test.js` -> `k6/scripts/load_test_auth.js`
- `load_test_rides.js` -> `k6/scripts/load_test_rides.js`

**Prerequisites:** API up (e.g. `docker compose up -d`); Swagger register works.

**Phone numbers:** `uniquePhone()` in `k6/lib/helpers.js` — blocks **`+972534XXXXXX`** and **`+972544XXXXXX`** (6-digit suffix, `phonenumbers`-friendly), salted with **`BASE_TS` / `__VU` / `userCounter`**.

**Before a load run (local/Docker):**

1. In **`backend/.env`** (temporary): set **`DEBUG=True`** and raise **`RATE_LIMIT_AUTH_MAX_REQUESTS`** (e.g. `10000`) so registration/login is not blocked by email verification or Redis rate limits.
2. Recreate the backend container so env is applied:  
   `docker compose up -d --force-recreate backend`  
   (`docker compose restart backend` is **not** enough — env is fixed at container create time.)
3. Optional: reset Redis DB 0 counters (e.g. `redis-cli … FLUSHDB`) — **warning:** clears other cache keys on DB 0 too.

```bash
# Install k6: https://grafana.com/docs/k6/latest/set-up/install-k6/
# From repo root:
k6 run --vus 10 --duration 30s backend/k6/scripts/load_test_auth.js

# From backend/:
k6 run k6/scripts/load_test_auth.js
```

**Summary output:** `handleSummary` prints to the console (no JSON file on disk). See `k6/README.md` and **`docs/ENGINEERING_HIGHLIGHTS.md`**.

**Pinned dependency:** `phonenumbers==8.13.48` in `pyproject.toml` / `uv.lock` — stable IL validation used by the API (see `app/core/utils/validators.py`).

## Groups — invite codes

- New groups receive a random **Base62** `invite_code` (8 characters, `secrets.choice` over `a-zA-Z0-9`).
- **`create_group`** uses **`flush`**, catches **`IntegrityError`**, and retries only when the violation is on **`invite_code`** uniqueness (PostgreSQL `23505` / message match); after **5** failed attempts it raises **`LinkUpError`** with **`INVITE_CODE_GENERATION_FAILED`**.
- A single **`commit`** persists the group and the creator’s **admin** `GroupMember` row. Implementation: **`app/domain/groups/crud.py`**.

## Media (S3, CloudFront, avatars)

- **Uploads:** clients use **presigned PUT** to S3 (see API routes for user avatar and group image); the API does not stream file bytes.
- **Public URLs:** when **`CLOUDFRONT_DOMAIN`** is set in `backend/.env` (see `app/core/config.py`), the storage layer builds **`https://{CLOUDFRONT_DOMAIN}/{key}`** for reads; otherwise **presigned GET** to S3 (`app/infrastructure/s3/service.py`).
- **Avatar pipeline:** staging key → outbox **`user.avatar_upload`** → **`avatar_upload_queue`** → worker resizes to WebP and writes under a **new versioned prefix** `avatars/{user_id}/v{version}/` (`app/infrastructure/s3/image_processor.py`, `app/workers/tasks/avatar_tasks.py`). The DB stores that prefix in **`users.avatar_key`**. The previous version’s prefix is deleted **only after** a successful DB commit; failed commits trigger best-effort cleanup of the new prefix. **Remove-avatar** clears `avatar_*` in Postgres + publishes **`user.avatar_remove`** (same transaction); the worker deletes the `avatars/{user_id}/` tree using streamed **`delete_objects`** batches (`iter_prefix_keys` + chunked **`delete_objects`** in `app/infrastructure/s3/`).
- **CORS:** browser uploads — `docs/S3_CORS.md`. **Schema / field notes:** `docs/architecture/DATABASE.md` (`users.avatar_key`).

## Geo caching updates

- Redis cache now stores geocoding results for 24 hours to reduce repeated calls for the same address input (**`geocode:{address}`** plus **`get_or_compute`** stampede guard in [`app/infrastructure/geo/geocode_cache.py`](app/infrastructure/geo/geocode_cache.py)).
- **Ride preview routing:** [`app/domain/geo/processor.py`](app/domain/geo/processor.py) **`get_full_routing_data`** resolves origin/destination text through **`get_coordinates`** (above), not duplicate bare **`GeocodingService`** calls per axis.
- The cache is fail-open: geo flows continue even if Redis is unavailable.
- This complements the existing 24h **full preview payload** Redis cache (`RideCacheRepository`) between preview and create steps.
- **Related read caps:** driver **`GET …/bookings/ride/{id}/manifest`** caps listed rows (**100**) with CONFIRMED-before-PENDING ordering + aggregate totals in response; **`GET …/passenger/passengers/me`** uses cursor pagination (`cursor`, `limit` -> `items`, `next_cursor`, `has_more`) — [`docs/architecture/API.md`](../docs/architecture/API.md), **`MANIFEST_BOOKING_ROW_LIMIT`** / **`PASSENGER_REQUESTS_*`** in [`app/core/constants.py`](app/core/constants.py).
