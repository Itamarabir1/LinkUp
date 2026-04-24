# Development Guide

הוראות הפעלה ופיתוח לוקאלי. מקור: `docker-compose.yml`, `backend/app/core/config.py`, `backend/pyproject.toml`.

---

## Prerequisites

- **Docker** ו-Docker Compose (להרצת db, **pgbouncer**, `redis-primary`/`redis-replica`/`redis-sentinel`, rabbitmq, backend, notification-worker, task-worker, ai-worker, chat-ws).
- **Python** 3.11+ (להרצת backend/worker לוקאלית בלי Docker).
- **Node** (אם מריצים פרונט — לא מפורט כאן).
- **Go** 1.x (אם בונים chat-ws ידנית).

---

## Setup

1. **Clone והעתקת env**
   - `.env` בשורש — העתק מ־`.env.example`: credentials ל־Compose בלבד (Postgres, Redis, RabbitMQ bootstrap); חייבים ליישר עם `backend/.env`.
   - `backend/.env` — העתק מ־`backend/.env.example`.
   - `chat-ws/.env` — העתק מ־`chat-ws/.env.example` (כולל `REDIS_URL`, `JWT_SECRET` זהה ל־`SECRET_KEY` בבקאנד).

2. **הרצה עם Docker**
  - `docker-compose.yml`: ל־`db`, **`pgbouncer`**, `redis`, `rabbitmq`, **`migrate`**, `notification-worker`, `task-worker`, `ai-worker`, `backend`, `chat-ws` **אין** `profiles` — עולים ב־`docker compose up -d`. **`migrate`** מריץ `alembic upgrade head` פעם אחת ויוצא (`restart: "no"`) ונשאר direct ל-`db`; **backend** וה־workers תלויים ב־`service_completed_successfully:migrate` וגם ב־`pgbouncer:service_healthy`. **backend** עם **`8000:8000`** ל־host, **healthcheck** על `/api/v1/health` (גוף התשובה כולל גם **`circuit_breakers`** למעגלי Google Maps — מידע תפעולי; **`status`** נקבע רק מ־DB/Redis/RabbitMQ — ראו **`docs/architecture/API.md`**). **`frontend`** ו־**`nginx`** מוגדרים באותו קובץ עם `profiles: ["prod"]` — עולים רק עם `docker compose --profile prod`; **nginx** תלוי ב־**backend** ב־`service_healthy`.
  - **PgBouncer image:** נבנה מקומית מ-`infrastructure/pgbouncer/Dockerfile` (ולא image ציבורי), כדי להבטיח שקובץ `pgbouncer.ini` הממופה ב-volume נשאר מקור אמת.
  - **פיתוח:** `docker compose up -d` → תשתית + **migrate** + 3 workers + backend (**8000**) + chat-ws (**8081**). פרונט: **`npm run dev`** בתיקיית `frontend`, לא קונטיינר.
   - **WebSocket בפיתוח:** צ'אט — `ws://localhost:8081/ws` (chat-ws); נסיעות / מיקום / **פיד התראות in-app** — `ws://localhost:8000/api/v1/...` (backend). מרוכז ב־[`frontend/src/config/env.ts`](../../frontend/src/config/env.ts).
   - **סטאק מלא מאחורי Nginx (פורט 80):** `docker compose --profile prod up -d --build`.
  - **FCM:** `firebase-credentials.json` ממופה read-only ל־**backend** ול־**notification-worker** (נתיב בקונטיינר: `/app/infrastructure/firebase_core/firebase-credentials.json`); `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env` חייב להתאים (הקובץ לא נכנס ל־image בגלל `.dockerignore`).
   - **שינוי `backend/.env`:** משתני הסביבה של מיכל ה-backend נטענים בעת **יצירת** הקונטיינר. אחרי עריכת הקובץ הרץ `docker compose up -d --force-recreate backend` (לא מספיק `docker compose restart backend`).

3. **הרצה לוקאלית (בלי Docker ל-backend / frontend)**
  - תשתיות + workers: `docker compose up -d` (או לפחות `db`, `redis`, `rabbitmq`, `chat-ws`; אם workers כבר רצים ב־Compose — **אל** תריץ במקביל worker מקומי נוסף). אם **לא** מרימים את שירות **`migrate`** בדוקר — להריץ ידנית `alembic upgrade head` לפני הבקאנד המקומי.
   - מתוך `backend/`: `alembic upgrade head`, ואז `uvicorn app.main:app --reload` (פורט 8000 — מתאים ל־`frontend` ב־dev, ראו `frontend/src/config/env.ts`).
  - Worker מקומי: רק אם **אין** workers בדוקר — הרץ entrypoint ייעודי (`python -m app.workers.notification_worker` / `task_worker` / `ai_worker`).

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | חובה | תיאור |
|----------|------|--------|
| POSTGRES_USER | כן (לוקאלי) | משתמש DB |
| POSTGRES_PASSWORD | כן | סיסמת DB |
| POSTGRES_DB | כן | שם DB |
| POSTGRES_HOST | — | localhost / db (Docker) |
| POSTGRES_PORT | — | 5432 |
| DB_POOL_SIZE | — | SQLAlchemy `pool_size` (ברירת מחדל 5) |
| DB_MAX_OVERFLOW | — | חיבורים נוספים תחת עומס (ברירת מחדל 10) |
| DB_POOL_TIMEOUT | — | שניות המתנה לחיבור מהמאגר (ברירת מחדל 30) |
| DB_POOL_RECYCLE | — | מחזור חיבורים בשניות (ברירת מחדל 1800) |
| DB pooling runtime path | — | runtime services דרך `pgbouncer`; migrations ישירות ל-`db` |
| DATABASE_URL | אופציונלי | override מלא (למשל פרודקשן / K8s / CI); נטען ל־`DATABASE_URL_RAW` ב־Settings דרך **`validation_alias`** (גם **`DATABASE_URL_RAW`** תקף כשם env) |
| REDIS_URL | אופציונלי | override מלא ל-Redis; נטען ל־`REDIS_URL_RAW` (גם **`REDIS_URL_RAW`** תקף) |
| REDIS_HOST | — | localhost / redis (alias ל-master ב-Compose) |
| REDIS_PORT | — | 6379 |
| REDIS_DB | — | 0 |
| REDIS_PASSWORD | — | אם Redis דורש סיסמה |
| REDIS_CHAT_DB | — | 1 (לצ'אט) |
| BACKEND_IMAGE | — | override ל-image של backend בפריסה (למשל `ghcr.io/<owner>/linkup/backend:<sha>`) |
| REDIS_SENTINEL_HOST | — | redis-sentinel (מפעיל נתיב Sentinel במקום URL רגיל) |
| REDIS_SENTINEL_PORT | — | 26379 |
| REDIS_MASTER_NAME | — | mymaster |
| RABBITMQ_HOST | — | localhost / rabbitmq |
| RABBITMQ_USER | כן | |
| RABBITMQ_PASSWORD | כן | |
| SECRET_KEY | כן (פרודקשן) | ל-JWT |
| ALGORITHM | — | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | — | 30 |
| REFRESH_TOKEN_EXPIRE_DAYS | — | 7 |
| FRONTEND_URL | — | כתובת הפרונט |
| API_PUBLIC_URL | — | כתובת ה-API בציבור |
| CORS_ORIGINS | — | רשימה מופרדת בפסיקים; אם ריק — משתמש ב-FRONTEND_URL |
| DEBUG | — | true/false |
| API_DOCS_ENABLED | — | false כברירת מחדל; true רק ב-dev/staging כדי לחשוף `/docs`/`/redoc`/`/openapi.json` |
| BREVO_API_KEY | למיילים | Brevo (Sendinblue) |
| BREVO_SENDER_EMAIL | — | |
| BREVO_SENDER_NAME | — | |
| STRIPE_SECRET_KEY | לחיובים | Stripe Secret Key (`sk_*` / `rk_*`) |
| STRIPE_PUBLISHABLE_KEY | אופציונלי בבקאנד | מפתח publishable; לרוב נצרך בפרונט כ-`VITE_STRIPE_PUBLISHABLE_KEY` |
| STRIPE_WEBHOOK_SECRET | לחתימת webhook | Stripe Webhook Signing Secret (`whsec_*`) |
| GOOGLE_MAPS_API_KEY | לגיאו/מפות | |
| GOOGLE_CLIENT_ID | ל-Google Sign-In | |
| GOOGLE_CLIENT_SECRET | אופציונלי | |
| EIA_API_KEY | לסריקת דלק | אופציונלי |
| AWS_ACCESS_KEY_ID | ל-S3 | אופציונלי |
| AWS_SECRET_ACCESS_KEY | | |
| AWS_REGION | — | eu-central-1 |
| S3_BUCKET_NAME | | |
| CLOUDFRONT_DOMAIN | מדיה ציבורית (אופציונלי) | דומיין CloudFront (ללא `https://`) — URLs ציבוריים לתמונות; בלי ערך — presigned GET ל-S3 |
| UPLOAD_TEMP_DIR | — | תיקייה לקבצים זמניים |
| FIREBASE_SERVICE_ACCOUNT_PATH | לפוש | |
| FIREBASE_CREDENTIALS_JSON | לפוש (פרודקשן) | |
| RATE_LIMIT_AUTH_WINDOW_SECONDS | — | 60 |
| RATE_LIMIT_AUTH_MAX_REQUESTS | — | 10 |
| FORCE_HTTPS_REDIRECT | — | false (true מאחורי proxy) |
| DOCKER_MODE | — | true ב-Docker |
| LOG_LEVEL | — | DEBUG / INFO / WARNING / ERROR (default: INFO) |
| LOG_FORMAT | — | text בפיתוח, json בפרודקשן |

### Chat-ws (`chat-ws/.env`)

| Variable | תיאור |
|----------|--------|
| PORT | 8081 |
| REDIS_URL | redis://[:password@]host:6379/1 |
| SECRET_KEY / JWT_SECRET | אותו ערך כמו ב-backend (לאימות JWT) |

---

## Backend tests (pytest)

- מתוך **`backend/`**: `uv run pytest tests/ -v`. דורש **PostgreSQL + PostGIS** עם סכמה מעודכנת — הרץ **`alembic upgrade head`** על אותו DB לפני הטסטים.
- **משתני סביבה:** ב־`tests/conftest.py` — **`DATABASE_URL`** (מומלץ), או **`TEST_DATABASE_URL`** (תאימות לאחור), או ברירת מחדל ל-docker-compose המקומי.
- **יישור עם CI:** ב-GitHub Actions הסדר בפועל הוא **Ruff check** → **Ruff format --check** → **`alembic upgrade head`** → **pytest** (עם **`DATABASE_URL` ברמת ה-job**) — ראו `.github/workflows/backend-ci.yml` ו־`backend/README.md`.

---

## Load testing (k6, optional)

סקריפטים Grafana **k6** מרוכזים תחת:

- [`backend/k6/scripts/load_test_auth.js`](../../backend/k6/scripts/load_test_auth.js)
- [`backend/k6/scripts/load_test_rides.js`](../../backend/k6/scripts/load_test_rides.js)
- [`backend/k6/scripts/load_test_users.js`](../../backend/k6/scripts/load_test_users.js)
- [`backend/k6/scripts/load_test_groups.js`](../../backend/k6/scripts/load_test_groups.js)
- [`backend/k6/scripts/load_test_chat.js`](../../backend/k6/scripts/load_test_chat.js)
- [`backend/k6/scripts/load_test_geo.js`](../../backend/k6/scripts/load_test_geo.js)
- [`backend/k6/scripts/load_test_ws.js`](../../backend/k6/scripts/load_test_ws.js)

Wrappers נשמרו לתאימות:
- [`backend/load_test.js`](../../backend/load_test.js)
- [`backend/load_test_rides.js`](../../backend/load_test_rides.js)

- **מה נבדק:** לכל איטרציה — `POST /api/v1/auth/register` ואז `POST /api/v1/auth/login`; מדדי משך ושגיאות; thresholds בקובץ.
- **טלפונים:** `k6/lib/helpers.js` — בלוקים **`+972534XXXXXX`** / **`+972544XXXXXX`** (סיומת 6 ספרות), מלח `BASE_TS` + **`__VU`** + מונה; תואם `phonenumbers` (IL).
- **לפני ריצה:** ב־`backend/.env` (זמנית, לבדיקות בלבד) מומלץ `DEBUG=True` (דילוג אימות אימייל בפיתוח) והעלאת **`RATE_LIMIT_AUTH_MAX_REQUESTS`** (למשל `10000`) כדי להימנע מ־429; אחר כך **`docker compose up -d --force-recreate backend`**. אופציונלי: איפוס מוני rate limit ב-Redis (`FLUSHDB` על DB 0) — **שימו לב:** מוחק גם cache אחר ב-DB 0.
- **הרצה:**

```bash
# מתוך שורש הפרויקט
k6 run --vus 10 --duration 30s backend/k6/scripts/load_test_auth.js
k6 run --vus 5 --duration 30s backend/k6/scripts/load_test_rides.js

# או מתוך backend/
cd backend && k6 run k6/scripts/load_test_auth.js
```

התקנת k6: <https://grafana.com/docs/k6/latest/set-up/install-k6/>. פירוט נוסף: `backend/README.md`, הערות בראש `load_test.js`, **`docs/ENGINEERING_HIGHLIGHTS.md`** (סעיף 12).

---

## Running Migrations

```bash
cd backend
alembic upgrade head
```

חזרה לאחור (צעד אחד):

```bash
alembic downgrade -1
```

יצירת migration חדש (לאחר שינוי מודלים):

```bash
alembic revision --autogenerate -m "description"
```

**Autogenerate ו-metadata:** ב־[`alembic/env.py`](../../backend/alembic/env.py) מיובא `app.db.models` אחרי `Base` כדי שכל טבלאות הדומיין יירשמו ב־`target_metadata` לפני השוואת סכמה. ב־API, אותו רישום מתחיל ב־[`app/api/v1/api_router.py`](../../backend/app/api/v1/api_router.py) (שורה ראשונה של ייבוא אפליקטיבי). Ruff: `per-file-ignores` ל־F401 על קבצי side-effect — [`backend/pyproject.toml`](../../backend/pyproject.toml).

---

## How To Recover From Partial Migration State

אם `alembic upgrade head` נכשל באמצע (למשל enum כבר קיים / עמודות חסרות), עובדים לפי סדר קבוע:

1. **בדיקת מצב נוכחי**
   - מתוך `backend/`: `alembic current`
   - ודא מה הרוויזיה בפועל מול `alembic heads`
2. **הרצת forward-only repair**
   - יש להריץ שוב `alembic upgrade head` (כולל migration תיקון forward-only, לא משכתבים migration ישן בסביבה משותפת)
3. **אימות סופי**
   - הרץ `bash ../scripts/ops/check-migration-head.sh` מתוך `backend/`
   - אם הסקריפט לא מחזיר `(head)` — לא ממשיכים להריץ טסטים/דיפלוי
4. **רק אם זו סביבת טסטים חד-פעמית**
   - אפשר לאפס DB ולבנות מחדש (`docker compose down -v` + `docker compose up -d db ...` + migrate)
   - בפרודקשן/סטייג׳ינג לא עושים reset, רק forward migrations

עקרון סניורי: **No history rewrite on shared environments** — מתקנים עם migration חדש בלבד (forward-only), כדי לשמור עקביות בין מפתחים, CI ופרודקשן.

---

## Project Structure

```
LinkUp/
├── backend/                 # FastAPI
│   ├── app/
│   │   ├── api/v1/          # Routers, api_router.py
│   │   ├── core/            # config, lifespan, middleware, exceptions
│   │   ├── db/              # session, base, models (imports domain)
│   │   ├── domain/          # Domain-Driven: users, rides, bookings, passengers, chat, groups, auth, events, admin
│   │   ├── infrastructure/  # redis, rabbitmq, outbox, events publishers, S3
│   │   ├── workers/         # main_worker, outbox_worker, tasks (notification, avatar, scheduled, chat_summary)
│   │   └── admin/           # SQLAdmin setup
│   ├── alembic/versions/    # 001–004
│   ├── k6/                  # k6 load tests (scripts + shared helpers)
│   ├── load_test.js         # wrapper תואם לאחור ל-auth k6
│   ├── load_test_rides.js   # wrapper תואם לאחור ל-rides k6
│   └── pyproject.toml       # תלויות + uv.lock (למשל phonenumbers==8.13.48)
├── chat-ws/                 # Go WebSocket server
│   ├── cmd/server/
│   ├── internal/auth, hub, redis
│   └── Dockerfile
├── docs/                    # architecture/*, ENGINEERING_HIGHLIGHTS, FCM_SYSTEM_SUMMARY, …
├── docker-compose.yml
└── ARCHITECTURE.md          # סקירה ברמה גבוהה
```

---

## Push (FCM) — Web

- פרונט: משתני `VITE_FIREBASE_*` + `VITE_FIREBASE_VAPID_KEY` ב־`frontend/.env` (ראה `frontend/.env.example`).
- בקאנד: `FIREBASE_CREDENTIALS_JSON` או `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env`.
- מחזור חיים (Web): רישום טוקן אחרי התחברות / טעינת סשן אם הרשאת דפדפן `granted`; ניקוי `fcm_token` בשרת + `cleanupFCM` ב־logout — פירוט ב־**`docs/FCM_SYSTEM_SUMMARY.md`** (סעיף Initialization).
- זרימה מלאה (FCM מהשרת: `data` בלבד; Service Worker; Toast ב־`App.tsx` + צליל בחזית): **`docs/FCM_SYSTEM_SUMMARY.md`**.

---

## Key Decisions

- **למה FastAPI ולא Django**: ביצועים אסינכרוניים, OpenAPI מובנה, התאמה ל-WebSocket ו-worker באותו שפה.
- **למה RabbitMQ ולא Kafka**: פשטות בסקלה הנוכחית, ניהול קל, Outbox pattern מספיק עם תור אחד/כמה תורים.
- **למה broker-native retry (DLX/TTL) במקום republish ידני**: פחות race conditions ו-state בקוד worker; ה-broker מנהל delay/requeue, וה-worker מתמקד ב-ack/nack.
- **למה PostgreSQL ולא MongoDB**: טרנזקציות, שלמות referential, PostGIS לגיאו, התאמה ל-ORM (SQLAlchemy).
- **Cursor-based vs Page-based Pagination**: נסיעות והודעות — זרימה אינסופית ויציבות עם cursor; הזמנות — מספור עמודים ו-total לממשק "הזמנות שלי".
- **למה PgBouncer עכשיו**: connection storms ב-EC2 קטן קורים לפני שנגמר CPU; pooler פנימי נותן שיפור מהיר בלי שינוי קוד דומיין.
- **מה לא טריוויאלי (senior)**: `migrate` נשאר direct ל-`db`, `statement_cache_size=0` ל-asyncpg, ו-PgBouncer נשאר internal-only בלי פתיחת פורט ציבורי.
- **Secrets ל-PgBouncer בפריסה**: `userlist.txt` לא נשמר ב-git; ה-CI deploy מייצר אותו מ-`userlist.txt.template` עם `envsubst`, מקשיח הרשאות (`chmod 600`), עושה build+up ל-`pgbouncer`, ממתין ל-health, ורק אז עושה rollout ל-backend.

---

## SLOs & Error Budgets (Ops baseline)

מטרת הסעיף: להפוך metrics ל-reliability contract תפעולי.

### 1) SLIs (מה מודדים)
- **Availability (API):** אחוז בקשות HTTP מוצלחות (2xx/3xx) מכלל הבקשות.
- **Latency (API):** `p95` ו-`p99` לנתיבים קריטיים.
- **Async reliability:** יחס הצלחה ב-Outbox/RabbitMQ (`processed` מול `failed`) + מגמות retries/DLQ.

### 2) SLO targets התחלתיים (מומלץ)
- **API availability:** 99.9% לחודש.
- **Latency:** `p95 < 400ms`, `p99 < 900ms`.
- **Async success ratio:** >= 99.5% לרכיבי outbox + worker pipelines.

### 3) Error budget policy
- אם יותר מ-50% מה-budget החודשי נצרך לפני אמצע החודש:
  - מקפיאים rollout של פיצ'רים לא קריטיים.
  - פותחים Reliability Sprint ממוקד ב-SLI שנפגע.
  - משחררים רק תיקוני יציבות/באגים עד חזרה למסלול.

### 4) Metric sources במערכת
- **Backend metrics endpoint:** `backend:8000/metrics`
- **Worker metrics endpoints:**
  - `notification-worker:9091/metrics`
  - `task-worker:9092/metrics`
  - `ai-worker:9093/metrics`
- Prometheus scrape מוגדר ב-`monitoring/prometheus.yml`.

---

## Recent backend architecture updates

- **Async refactor (passengers/bookings/rides):** רוב זרימות הליבה עברו ל-SQLAlchemy async (`AsyncSession`, `select/execute`) כדי לשפר throughput ולשמור שרשרת async נקייה בין router -> service -> crud. **מסך “הזמנות שלי” (ווב):** endpoints מאוגדים `GET /bookings/driver-summary` ו־`GET /bookings/passenger-summary` עם `joinedload` / `with_loader_criteria` — ראו `docs/architecture/DATABASE.md` ו־`API.md`.
- **Async end-to-end (API + workers):** **Bookings** וזרימות ליבה async-only; workers (למשל `app/workers/tasks/notification_tasks.py`) משתמשים ב־`await db.execute(select(...))` — אין `Session.run_sync` בקוד האפליקציה. `run_sync` נשאר רק ב־Alembic (`alembic/env.py`) עבור מיגרציות.
- **Geocode cache (24h):** כתובות שחוזרות על עצמן נשמרות ב-Redis ל-24 שעות כדי לחסוך קריאות **Google Geocoding** ולשפר latency.
- **Admin API + מסך אדמין:** `GET/PATCH … /api/v1/admin/*` דרך `get_current_admin_user`; ממשק React ב־`frontend/src/features/admin/` (`/admin`, lazy). פירוט: **`ADMIN_DASHBOARD.md`** בשורש ה-repo.
- **RabbitMQ reliability refactor (PR1+PR2):** נוספו `run_supervised` + `ConsumerSupervisor` עם draining states ו-`max_retries`; ה-messaging path פוצל ל-clients לפי תפקיד (`rabbit_client`/`outbox_rabbit_client`/`worker_rabbit_client`) עם channel isolation ל-consumers. Queue config מרוכז ב-`backend/app/infrastructure/rabbitmq/topology.py` (`QueueSpec`).
- **RabbitMQ PR3/PR4/PR5:** retry עבר ל-broker-native DLX/TTL + `x-death`; נוסף `run_dlq_monitor` לניטור עומק DLQ; ונוסף כלי תפעולי `scripts/ops/rabbitmq-dlq-replay.py` ל-replay מבוקר מתורי DLQ.

---

## RabbitMQ DLQ Replay Tool

- קובץ: `scripts/ops/rabbitmq-dlq-replay.py`
- שימוש:
  - dry-run: `python scripts/ops/rabbitmq-dlq-replay.py --dry-run`
  - replay ברירת מחדל ל-queues retry-enabled: `python scripts/ops/rabbitmq-dlq-replay.py --limit 100`
  - replay לתור ספציפי: `python scripts/ops/rabbitmq-dlq-replay.py --queue notifications_queue --limit 50`
- הכלי מחזיר הודעות מ-`<queue>.dlq` חזרה לתור הראשי `<queue>` ומדפיס דוח JSON עם `replayed/errors/remaining`.
