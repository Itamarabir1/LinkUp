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
   ```bash
   docker compose up -d
   ```
   - Backend רץ עם `alembic upgrade head && gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`.
   - Outbox-worker: `python -m app.workers.main_worker`.
   - Chat-ws: פורט 8081.

3. **הרצה לוקאלית (בלי Docker ל-backend)**
   - הפעל רק db, redis, rabbitmq: `docker compose up -d db redis rabbitmq`.
   - מתוך `backend/`: `alembic upgrade head`, ואז `uvicorn app.main:app --reload` (פיתוח לוקאלי) או `gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000` (פרודקשן).
   - Worker בנפרד: `python -m app.workers.main_worker`.

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
├── docs/                    # DATABASE.md, API.md, EVENTS.md, REALTIME.md, DEVELOPMENT.md
├── docker-compose.yml
└── ARCHITECTURE.md          # סקירה ברמה גבוהה
```

---

## Key Decisions

- **למה FastAPI ולא Django**: ביצועים אסינכרוניים, OpenAPI מובנה, התאמה ל-WebSocket ו-worker באותו שפה.
- **למה RabbitMQ ולא Kafka**: פשטות בסקלה הנוכחית, ניהול קל, Outbox pattern מספיק עם תור אחד/כמה תורים.
- **למה PostgreSQL ולא MongoDB**: טרנזקציות, שלמות referential, PostGIS לגיאו, התאמה ל-ORM (SQLAlchemy).
- **Cursor-based vs Page-based Pagination**: נסיעות והודעות — זרימה אינסופית ויציבות עם cursor; הזמנות — מספור עמודים ו-total לממשק "הזמנות שלי".
