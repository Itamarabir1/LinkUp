# Linkup Backend

FastAPI application: auth, rides, bookings, notifications, chat, workers.

## Running locally (development)

- **Windows**: `run-backend.bat` — stops any process on port 8000, then runs `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Linux / macOS**: `./run-backend.sh` (make executable first: `chmod +x run-backend.sh`)

For production, use Docker (see root `docker-compose.yml`).  
**Push (FCM):** ב־Compose קובץ השירות של Firebase נטען מ־volume לנתיב בקונטיינר; הגדר `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env` (גם ל־`outbox-worker`) — פירוט ב־`docs/FCM_SYSTEM_SUMMARY.md` וב־README בשורש.

## Environment

Copy `.env.example` to `.env` and set your values. See root README for full setup.

**Database connection pool** (optional tuning): `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE` — documented in `.env.example` and `docs/architecture/DEVELOPMENT.md`.

## Security & auth (backend)

- **Password hashing:** bcrypt (passlib); `get_password_hash` / `verify_password` are **async** and offload CPU work via `asyncio.get_running_loop().run_in_executor` so the ASGI event loop stays responsive under load.
- **Rate limiting:** Redis-backed limiter on **`POST /api/v1/auth/register`** and other sensitive auth routes (see `app/api/dependencies/rate_limit.py`); window/size from `RATE_LIMIT_AUTH_*` in config.
- **Email / reset OTP:** `VerificationService` uses **`secrets`** for codes, **`hmac.compare_digest`** for comparison, Redis-backed **attempt counter** (brute-force guard), counter **reset** when a new OTP is issued — see `app/domain/auth/verification_service.py`.

Portfolio-style summary: **`docs/ENGINEERING_HIGHLIGHTS.md`**.

## Migrations

Alembic is in `alembic/`. Run migrations with:

```bash
alembic upgrade head
```

## Load testing (k6)

Focused auth load test: `load_test.js` — ramp to 500 VUs, register + login per iteration, separate thresholds for errors and p95 latency.

Before running: ensure `docker-compose up --build` is healthy and you can register a user via Swagger.

```bash
# Install k6 once: https://k6.io/docs/get-started/installation/
cd backend
k6 run load_test.js
```

Writes `load_test_summary.json` in the current working directory.
