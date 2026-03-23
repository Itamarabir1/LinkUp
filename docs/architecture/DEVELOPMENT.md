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
   - `backend/.env` — העתק מ-`.env.example` אם קיים, או צור לפי הרשימה למטה.
   - `chat-ws/.env` — PORT, REDIS_URL, SECRET_KEY (JWT).

2. **הרצה עם Docker**
   - `docker-compose.yml`: ל־`db`, `redis`, `rabbitmq`, `outbox-worker`, `backend`, `chat-ws` **אין** `profiles` — עולים ב־`docker compose up -d`. **backend** עם **`8000:8000`** ל־host (Vite מקומי → API). ל־**nginx** יש `profiles: ["prod"]` בבסיס; **`frontend` (סטטי)** מוגדר ב־`docker-compose.override.yml` עם `profiles: ["prod"]` — בלי override מתאים, `docker compose --profile prod` ייכשל (`nginx` תלוי ב־`frontend`).
   - `docker-compose.override.yml` (מומלץ; העתק מ־`docker-compose.override.yml.example`) — `nginx` + `frontend` עם `profiles: ["prod"]` והגדרת build מלאה ל־frontend.
   - **פיתוח:** `docker compose up -d` → תשתית + worker + backend (**8000**) + chat-ws (**8081**). פרונט: **`npm run dev`** על המחשב, לא קונטיינר frontend.
   - **סטאק מלא מאחורי Nginx (פורט 80):** `docker compose --profile prod up -d` (עם override).
   - **FCM:** `firebase-credentials.json` ממופה read-only ל־**backend** ול־**outbox-worker** (נתיב בקונטיינר: `/app/infrastructure/firebase_core/firebase-credentials.json`); `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env` חייב להתאים (הקובץ לא נכנס ל־image בגלל `.dockerignore`).

3. **הרצה לוקאלית (בלי Docker ל-backend / frontend)**
   - תשתיות + worker: `docker compose up -d` (או לפחות `db`, `redis`, `rabbitmq`, `chat-ws`; אם `outbox-worker` כבר רץ ב־Compose — **אל** תריץ במקביל `python -m app.workers.main_worker` מקומית).
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
│   │   ├── domain/          # Domain-Driven: users, rides, bookings, passengers, chat, groups, auth, events
│   │   ├── infrastructure/  # redis, rabbitmq, outbox, events publishers, S3
│   │   ├── workers/         # main_worker, outbox_worker, tasks (notification, avatar, scheduled, chat_summary)
│   │   └── admin/           # SQLAdmin setup
│   ├── alembic/versions/    # 001–004
│   └── pyproject.toml       # תלויות (אין requirements.txt)
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
