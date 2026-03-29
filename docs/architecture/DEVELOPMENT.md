# Development Guide

הוראות הפעלה ופיתוח לוקאלי. מקור: `docker-compose.yml`, `backend/app/core/config.py`, `backend/pyproject.toml`.

---

## Prerequisites

- **Docker** ו-Docker Compose (להרצת db, redis, rabbitmq, backend, outbox-worker, chat-ws).
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
   - `docker-compose.yml`: ל־`db`, `redis`, `rabbitmq`, **`migrate`**, `outbox-worker`, `backend`, `chat-ws` **אין** `profiles` — עולים ב־`docker compose up -d`. **`migrate`** מריץ `alembic upgrade head` פעם אחת ויוצא (`restart: "no"`); **backend** ו־**outbox-worker** תלויים ב־`service_completed_successfully:migrate`. **backend** עם **`8000:8000`** ל־host, **healthcheck** על `/api/v1/health`. **`frontend`** ו־**`nginx`** מוגדרים באותו קובץ עם `profiles: ["prod"]` — עולים רק עם `docker compose --profile prod`; **nginx** תלוי ב־**backend** ב־`service_healthy`.
   - **פיתוח:** `docker compose up -d` → תשתית + **migrate** + worker + backend (**8000**) + chat-ws (**8081**). פרונט: **`npm run dev`** בתיקיית `frontend`, לא קונטיינר.
   - **סטאק מלא מאחורי Nginx (פורט 80):** `docker compose --profile prod up -d --build`.
   - **FCM:** `firebase-credentials.json` ממופה read-only ל־**backend** ול־**outbox-worker** (נתיב בקונטיינר: `/app/infrastructure/firebase_core/firebase-credentials.json`); `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env` חייב להתאים (הקובץ לא נכנס ל־image בגלל `.dockerignore`).
   - **שינוי `backend/.env`:** משתני הסביבה של מיכל ה-backend נטענים בעת **יצירת** הקונטיינר. אחרי עריכת הקובץ הרץ `docker compose up -d --force-recreate backend` (לא מספיק `docker compose restart backend`).

3. **הרצה לוקאלית (בלי Docker ל-backend / frontend)**
   - תשתיות + worker: `docker compose up -d` (או לפחות `db`, `redis`, `rabbitmq`, `chat-ws`; אם `outbox-worker` כבר רץ ב־Compose — **אל** תריץ במקביל `python -m app.workers.main_worker` מקומית). אם **לא** מרימים את שירות **`migrate`** בדוקר — להריץ ידנית `alembic upgrade head` לפני הבקאנד המקומי.
   - מתוך `backend/`: `alembic upgrade head`, ואז `uvicorn app.main:app --reload` (פורט 8000 — מתאים ל־`frontend` ב־dev, ראו `frontend/src/config/env.ts`).
   - Worker מקומי: רק אם **אין** `outbox-worker` בדוקר — `python -m app.workers.main_worker`.

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
| DATABASE_URL | אופציונלי | override מלא (למשל פרודקשן / K8s) |
| REDIS_HOST | — | localhost / redis |
| REDIS_PORT | — | 6379 |
| REDIS_DB | — | 0 |
| REDIS_PASSWORD | — | אם Redis דורש סיסמה |
| REDIS_CHAT_DB | — | 1 (לצ'אט) |
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
| BREVO_API_KEY | למיילים | Brevo (Sendinblue) |
| BREVO_SENDER_EMAIL | — | |
| BREVO_SENDER_NAME | — | |
| GOOGLE_MAPS_API_KEY | לגיאו/מפות | |
| GOOGLE_CLIENT_ID | ל-Google Sign-In | |
| GOOGLE_CLIENT_SECRET | אופציונלי | |
| EIA_API_KEY | לסריקת דלק | אופציונלי |
| AWS_ACCESS_KEY_ID | ל-S3 | אופציונלי |
| AWS_SECRET_ACCESS_KEY | | |
| AWS_REGION | — | eu-central-1 |
| S3_BUCKET_NAME | | |
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

---

## Project Structure

```
Linkup/
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
- זרימה מלאה (FCM מהשרת: `data` בלבד; Service Worker; Toast + צליל בחזית): **`docs/FCM_SYSTEM_SUMMARY.md`**.

---

## Key Decisions

- **למה FastAPI ולא Django**: ביצועים אסינכרוניים, OpenAPI מובנה, התאמה ל-WebSocket ו-worker באותו שפה.
- **למה RabbitMQ ולא Kafka**: פשטות בסקלה הנוכחית, ניהול קל, Outbox pattern מספיק עם תור אחד/כמה תורים.
- **למה PostgreSQL ולא MongoDB**: טרנזקציות, שלמות referential, PostGIS לגיאו, התאמה ל-ORM (SQLAlchemy).
- **Cursor-based vs Page-based Pagination**: נסיעות והודעות — זרימה אינסופית ויציבות עם cursor; הזמנות — מספור עמודים ו-total לממשק "הזמנות שלי".

---

## Recent backend architecture updates

- **Async refactor (passengers/bookings/rides):** רוב זרימות הליבה עברו ל-SQLAlchemy async (`AsyncSession`, `select/execute`) כדי לשפר throughput ולשמור שרשרת async נקייה בין router -> service -> crud.
- **Selective sync retention:** `db.run_sync(...)` עדיין קיים במקומות שבהם נשאר CRUD סינכרוני נקודתית. **Bookings** עברו ל־async-only, כולל נעילות עם `select(...).with_for_update()` (ללא `db.run_sync`), כדי לשמור שרשרת async נקייה.
- **Geocode cache (24h):** כתובות שחוזרות על עצמן נשמרות ב-Redis ל-24 שעות כדי לחסוך קריאות **Google Geocoding** ולשפר latency.
- **Admin API + מסך אדמין:** `GET/PATCH … /api/v1/admin/*` דרך `get_current_admin_user`; ממשק React ב־`frontend/src/features/admin/` (`/admin`, lazy). פירוט: **`ADMIN_DASHBOARD.md`** בשורש ה-repo.
