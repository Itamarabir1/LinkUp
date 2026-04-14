# Linkup Backend

FastAPI application: auth, rides, bookings, notifications, chat, workers.

## Running locally (development)

- **Windows**: `run-backend.bat` — stops any process on port 8000, then runs `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Linux / macOS**: `./run-backend.sh` (make executable first: `chmod +x run-backend.sh`)

For production, use Docker (see root `docker-compose.yml`).

- **Uvicorn workers (Docker):** `backend/entrypoint.sh` מריץ `uvicorn ... --workers` לפי **`UVICORN_WORKERS`** ב-`backend/.env` (ברירת מחדל 1). ב-`.env.example`: **`UVICORN_WORKERS=4`**. פיתוח לוקאלי בלי דוקר: `run-backend.sh` / `run-backend.bat` — `--reload`, worker אחד.
- **WebSocket auth:** `get_current_user_ws` מאמת **JWT בלבד** (אובייקט `WsUser`), בלי `SELECT` ל-DB בזמן חיבור — ראו `app/api/dependencies/auth.py`. HTTP endpoints עם `get_current_user` עדיין טוענים משתמש מ-DB.

**Push (FCM):** ב־Compose קובץ השירות של Firebase נטען מ־volume לנתיב בקונטיינר; הגדר `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env` (גם ל־`outbox-worker`) — פירוט ב־`docs/FCM_SYSTEM_SUMMARY.md` וב־README בשורש.

## Email rendering architecture

- Email HTML rendering now runs through a dedicated **Node.js + Express + React Email** service in `../email-renderer/`.
- Backend/outbox-worker call [`app/domain/notifications/channels/email/renderer.py`](app/domain/notifications/channels/email/renderer.py), which delegates to:
  - `POST {EMAIL_RENDERER_URL}/render` with `{ template, props }`
- Configure endpoint in `backend/.env`:
  - `EMAIL_RENDERER_URL=http://email-renderer:3001`
- Template names are mapped in [`app/domain/notifications/config/templates_map/email_conf.py`](app/domain/notifications/config/templates_map/email_conf.py) as **PascalCase** registry keys (not Jinja paths).
- Compose runtime expects `email-renderer` healthy before `backend`/`outbox-worker` start.

## Environment

Copy `.env.example` to `.env` and set your values. See root README for full setup.

**Database connection pool** (optional tuning): `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE` — documented in `.env.example` and `docs/architecture/DEVELOPMENT.md`.

## Security & auth (backend)

- **Password hashing:** bcrypt (passlib); `get_password_hash` / `verify_password` are **async** and offload CPU work via `asyncio.get_running_loop().run_in_executor` so the ASGI event loop stays responsive under load.
- **Rate limiting:** Redis-backed limiter on **`POST /api/v1/auth/register`** and other sensitive auth routes (see `app/api/dependencies/rate_limit.py`); window/size from `RATE_LIMIT_AUTH_*` in config.
- **Username enumeration (OWASP):** `authenticate_and_create_token` raises the same **`InvalidCredentialsError`** (401) for unknown email and wrong password so clients cannot infer whether an account exists. Covered in `tests/test_auth.py` (with `DATABASE_URL`).
- **Email / reset OTP:** `VerificationService` uses **`secrets`** for codes, **`hmac.compare_digest`** for comparison, Redis-backed **attempt counter** (brute-force guard), counter **reset** when a new OTP is issued — see `app/domain/auth/verification_service.py`.

Portfolio-style summary: **`docs/ENGINEERING_HIGHLIGHTS.md`**.

## Tests & CI (quality)

- **pytest:** מתוך `backend/` — `uv run pytest tests/ -v`. טסטי אינטגרציה עם DB דורשים **PostgreSQL + PostGIS** וסכמה מעודכנת (**`alembic upgrade head`** על אותו DB). ב־`tests/conftest.py` מקור ה-DSN: **`DATABASE_URL`** (עדיפות), או **`TEST_DATABASE_URL`** (תאימות לאחור), או ברירת מחדל ל-docker-compose המקומי.
- **GitHub Actions** (`.github/workflows/backend-ci.yml`): שירות Postgres, **`DATABASE_URL` ברמת ה-job** (מיפוי אחיד ל־**Alembic** ול־**pytest**), שלבי איכות בסדר בפועל: **Ruff check** → **Ruff format --check** → **`uv run alembic upgrade head`** → **`uv run pytest`**. קבצים תחת `alembic/` נכללים ב־autogenerate דרך `env.py` (ייבוא `app.db.models`); אם CI ירחיב ל־`ruff check alembic/`, ה־`per-file-ignores` ל־`alembic/env.py` מכסה F401 על ייבוא registry.
- **Settings:** משתני סביבה **`DATABASE_URL`** / **`REDIS_URL`** נקראים ל־`DATABASE_URL_RAW` / `REDIS_URL_RAW` דרך **`validation_alias=AliasChoices(...)`** ב־`app/core/config.py` (pydantic-settings) — כך Alembic (`settings.DATABASE_URL`) והריצה ב-CI מסתנכרנים.

**Error responses (JSON, `error_code`, `trace_id`, handlers):** [`docs/ERRORS.md`](../docs/ERRORS.md).

**Logging (JSON):** בפרודקשן `LOG_FORMAT=json` עם **python-json-logger** (v3+). ה-formatter נטען מ־`pythonjsonlogger.json` — בקוד: `from pythonjsonlogger import json as jsonlogger` ב־`app/core/logging.py`.

## Admin API (`/api/v1/admin`)

Endpoints for operators only: FastAPI dependency **`get_current_admin_user`** (`app/api/dependencies/admin.py`) requires `User.is_admin`. Router: **`app/domain/admin/router.py`**, mounted in **`app/api/v1/api_router.py`** with prefix **`/admin`**. Includes stats, health, user list + PATCH (active/admin flag), rides/groups lists and ride cancel, outbox list/detail + requeue for FAILED events, ride/booking lookup; sensitive actions log with **`[admin_audit]`**.  
**Web UI** lives in the main frontend: **`frontend/src/features/admin/`** → routes under **`/admin`** — see root **`ADMIN_DASHBOARD.md`**.

## Bookings — aggregated reads (My Bookings)

- **`GET /api/v1/bookings/driver-summary`** (auth): all rides for the current driver with **pending + confirmed** bookings and passenger contact fields in **one** `AsyncSession.execute` — `CRUDBooking.get_driver_rides_with_passengers` uses `joinedload(Ride.bookings → passenger_request → user)`, `joinedload(Ride.group)`, and `with_loader_criteria(Booking, …)` so cancelled/rejected rows are not loaded into the collection.
- **`GET /api/v1/bookings/passenger-summary`** (auth): all bookings for the current passenger with ride, **driver**, and **group** in **one** query — `get_passenger_bookings_with_rides`.
- **Shared manifest mapping:** `BookingService._booking_to_manifest_item` feeds both the per-ride manifest endpoint and driver-summary passengers.
- **GPS REST:** `BookingService.broadcast_driver_location` / `broadcast_passenger_location` centralize permission checks; routers delegate only.
- **Frontend contract:** web client consumes these endpoints via `fetchDriverSummary` / `fetchPassengerSummary` and maps payloads in `frontend/src/pages/MyBookings/myBookings.mappers.ts` to keep transport DTOs decoupled from UI view models.

See `docs/architecture/API.md` and `docs/architecture/DATABASE.md`.

## Async architecture updates (rides / bookings / passengers)

- Core flows in passenger requests, bookings, and rides were refactored to SQLAlchemy 2.0 async patterns:
  - `AsyncSession` usage in API/service paths
  - `select(...)` + `await db.execute(...)` for async querying
  - `await db.flush()` / `await db.commit()` in async transaction boundaries
- **Bookings are async-only** now (no `db.run_sync`): lock-critical paths use `select(...).with_for_update()` directly on `AsyncSession` to prevent races while keeping the call chain fully async.
- **Workers:** notification handlers (e.g. `notification_tasks.py` — ride created, booking approved, **ride cancelled**) query with `await db.execute(select(...))`; `find_passengers_for_ride_notification` is async. No `db.run_sync` in application code (Alembic `env.py` still uses `connection.run_sync` for migrations).
- Result: lower event-loop blocking risk, cleaner async call chains, and safer concurrency in booking/ride state transitions.

## SQLAlchemy model registry (imports)

- **[`app/api/v1/api_router.py`](app/api/v1/api_router.py)** begins with `import app.db.models` so domain routers load after required ORM models are registered on `Base.metadata` (avoids string-relationship resolution errors and import-order surprises). This registry is intentionally focused on API/domain relationship loading and is not a claim that every ORM class in the repository is re-exported there.
- **[`alembic/env.py`](alembic/env.py)** imports `app.db.models` after `Base` so **`target_metadata`** includes all tables for **`alembic revision --autogenerate`**.
- **`main.py`** may still import `app.db.models` before `api_router` for clarity; duplicate import is harmless.

**Ruff:** side-effect imports are allowed via **`[tool.ruff.lint.per-file-ignores]`** for **`F401`** on `api_router.py`, `app/db/models.py`, `alembic/env.py`, and `app/workers/main_worker.py` — see [`pyproject.toml`](pyproject.toml).

## Migrations

Alembic is in `alembic/`. Run migrations with:

```bash
alembic upgrade head
```

With **Docker Compose** at the repo root, the **`migrate`** service runs `alembic upgrade head` once before **backend** and **outbox-worker** start; the production **Dockerfile** does **not** run migrations in `CMD` (only `gunicorn` / `uvicorn`). If you deploy **without** Compose (e.g. raw image or Kubernetes), run migrations as a one-off Job, init container, or CI step — do not rely on the API container entrypoint alone.

**Recent:** קובץ **`007_add_last_active_at.py`** — מזהה רוויזיה ב-Alembic: **`007_last_active_at`** (`users.last_active_at`). **`008_scheduled_notifications`** — `down_revision` חייב להיות **`007_last_active_at`** (לא שם הקובץ); טבלת `scheduled_notifications`, אינדקס חלקי, הסרת `reminder_sent` מ-rides/bookings. ORM, API וטיפוסי הפרונט מיושרים (אין `reminder_sent` בתגובות / ב-`frontend` types). See `docs/architecture/DATABASE.md` and `docs/architecture/EVENTS.md`.

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
- **`create_group`** uses **`flush`**, catches **`IntegrityError`**, and retries only when the violation is on **`invite_code`** uniqueness (PostgreSQL `23505` / message match); after **5** failed attempts it raises **`LinkupError`** with **`INVITE_CODE_GENERATION_FAILED`**.
- A single **`commit`** persists the group and the creator’s **admin** `GroupMember` row. Implementation: **`app/domain/groups/crud.py`**.

## Media (S3, CloudFront, avatars)

- **Uploads:** clients use **presigned PUT** to S3 (see API routes for user avatar and group image); the API does not stream file bytes.
- **Public URLs:** when **`CLOUDFRONT_DOMAIN`** is set in `backend/.env` (see `app/core/config.py`), the storage layer builds **`https://{CLOUDFRONT_DOMAIN}/{key}`** for reads; otherwise **presigned GET** to S3 (`app/infrastructure/s3/service.py`).
- **Avatar pipeline:** staging key → RabbitMQ **`avatar_upload_queue`** → worker resizes to WebP and writes under a **new versioned prefix** `avatars/{user_id}/v{version}/` (`app/infrastructure/s3/image_processor.py`, `app/workers/tasks/avatar_tasks.py`). The DB stores that prefix in **`users.avatar_key`**. The previous version’s prefix is deleted **only after** a successful DB commit; failed commits trigger best-effort cleanup of the new prefix. **Remove-avatar** still deletes the whole `avatars/{user_id}/` tree in S3.
- **CORS:** browser uploads — `docs/S3_CORS.md`. **Schema / field notes:** `docs/architecture/DATABASE.md` (`users.avatar_key`).

## Geo caching updates

- Redis cache now stores geocoding results for 24 hours to reduce repeated calls for the same address input.
- The cache is fail-open: geo flows continue even if Redis is unavailable.
- This complements the existing 24h ride-preview cache and reduces external API pressure during repeated searches.
