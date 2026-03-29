# Linkup Backend

FastAPI application: auth, rides, bookings, notifications, chat, workers.

## Running locally (development)

- **Windows**: `run-backend.bat` — stops any process on port 8000, then runs `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Linux / macOS**: `./run-backend.sh` (make executable first: `chmod +x run-backend.sh`)

For production, use Docker (see root `docker-compose.yml`).

- **Uvicorn workers:** הקונטיינר מריץ `uvicorn ... --workers ${UVICORN_WORKERS:-1}`. מגדירים ב-`backend/.env` — ב-`.env.example` מופיע **`UVICORN_WORKERS=4`**. בלי משתנה: ברירת המחדל ב-Compose היא תהליך יחיד. פיתוח לוקאלי עם `--reload` — בדרך כלל worker אחד.
- **WebSocket auth:** `get_current_user_ws` מאמת **JWT בלבד** (אובייקט `WsUser`), בלי `SELECT` ל-DB בזמן חיבור — ראו `app/api/dependencies/auth.py`. HTTP endpoints עם `get_current_user` עדיין טוענים משתמש מ-DB.

**Push (FCM):** ב־Compose קובץ השירות של Firebase נטען מ־volume לנתיב בקונטיינר; הגדר `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env` (גם ל־`outbox-worker`) — פירוט ב־`docs/FCM_SYSTEM_SUMMARY.md` וב־README בשורש.

## Environment

Copy `.env.example` to `.env` and set your values. See root README for full setup.

**Database connection pool** (optional tuning): `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE` — documented in `.env.example` and `docs/architecture/DEVELOPMENT.md`.

## Security & auth (backend)

- **Password hashing:** bcrypt (passlib); `get_password_hash` / `verify_password` are **async** and offload CPU work via `asyncio.get_running_loop().run_in_executor` so the ASGI event loop stays responsive under load.
- **Rate limiting:** Redis-backed limiter on **`POST /api/v1/auth/register`** and other sensitive auth routes (see `app/api/dependencies/rate_limit.py`); window/size from `RATE_LIMIT_AUTH_*` in config.
- **Username enumeration (OWASP):** `authenticate_and_create_token` raises the same **`InvalidCredentialsError`** (401) for unknown email and wrong password so clients cannot infer whether an account exists. Covered in `tests/test_auth.py` (with `TEST_DATABASE_URL`).
- **Email / reset OTP:** `VerificationService` uses **`secrets`** for codes, **`hmac.compare_digest`** for comparison, Redis-backed **attempt counter** (brute-force guard), counter **reset** when a new OTP is issued — see `app/domain/auth/verification_service.py`.

Portfolio-style summary: **`docs/ENGINEERING_HIGHLIGHTS.md`**.

**Error responses (JSON, `error_code`, `trace_id`, handlers):** [`docs/ERRORS.md`](../docs/ERRORS.md).

## Admin API (`/api/v1/admin`)

Endpoints for operators only: FastAPI dependency **`get_current_admin_user`** (`app/api/dependencies/admin.py`) requires `User.is_admin`. Router: **`app/domain/admin/router.py`**, mounted in **`app/api/v1/api_router.py`** with prefix **`/admin`**. Includes stats, health, user list + PATCH (active/admin flag), rides/groups lists and ride cancel, outbox list/detail + requeue for FAILED events, ride/booking lookup; sensitive actions log with **`[admin_audit]`**.  
**Web UI** lives in the main frontend: **`frontend/src/features/admin/`** → routes under **`/admin`** — see root **`ADMIN_DASHBOARD.md`**.

## Async architecture updates (rides / bookings / passengers)

- Core flows in passenger requests, bookings, and rides were refactored to SQLAlchemy 2.0 async patterns:
  - `AsyncSession` usage in API/service paths
  - `select(...)` + `await db.execute(...)` for async querying
  - `await db.flush()` / `await db.commit()` in async transaction boundaries
- **Bookings are async-only** now (no `db.run_sync`): lock-critical paths use `select(...).with_for_update()` directly on `AsyncSession` to prevent races while keeping the call chain fully async.
- `db.run_sync(...)` may still appear in other parts of the backend where legacy sync CRUD is used (e.g., some ride/passenger flows or worker tasks).
- Result: lower event-loop blocking risk, cleaner async call chains, and safer concurrency in booking/ride state transitions.

## Migrations

Alembic is in `alembic/`. Run migrations with:

```bash
alembic upgrade head
```

With **Docker Compose** at the repo root, the **`migrate`** service runs `alembic upgrade head` once before **backend** and **outbox-worker** start; the production **Dockerfile** does **not** run migrations in `CMD` (only `gunicorn` / `uvicorn`). If you deploy **without** Compose (e.g. raw image or Kubernetes), run migrations as a one-off Job, init container, or CI step — do not rely on the API container entrypoint alone.

**Recent:** revision **`007_last_active_at`** adds `users.last_active_at` (chat activity / last-seen from chat-ws debounce), distinct from `last_login`. See `docs/architecture/DATABASE.md` and `docs/architecture/REALTIME.md`.

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

## Geo caching updates

- Redis cache now stores geocoding results for 24 hours to reduce repeated calls for the same address input.
- The cache is fail-open: geo flows continue even if Redis is unavailable.
- This complements the existing 24h ride-preview cache and reduces external API pressure during repeated searches.
