# Linkup — Architecture Overview

תיעוד רמה גבוהה של המערכת. לעדכונים מפורטים: `docs/DATABASE.md`, `docs/API.md`, `docs/EVENTS.md`, `docs/architecture/REALTIME.md`, `docs/DEVELOPMENT.md`. **להצגת הפרויקט (פיצ’רים, סקייל, טריקים):** `docs/ENGINEERING_HIGHLIGHTS.md`.

---

## Services

| Service | Path | Language | Port | Purpose |
|---------|------|----------|------|---------|
| backend | backend/ | Python / FastAPI | 8000 | REST API, auth, rides, bookings, chat, groups, geo |
| outbox-worker | backend/ (same image) | Python | — | Outbox → RabbitMQ, notifications, avatar tasks, scheduled, chat completion |
| chat-ws | chat-ws/ | Go | 8081 | WebSocket server for real-time chat (JWT, Redis Pub/Sub) |
| db | Docker | PostgreSQL 15 + PostGIS | 5432 | Primary data store |
| redis | Docker | Redis Stack 7.2 | 6379 | **שרת Redis אחד** — DB 0: backend/worker; DB 1: chat-ws (צ'אט, presence, `user:offline`, completion) |
| rabbitmq | Docker | RabbitMQ 3 + Management | 5672, 15672 | Message broker (events, tasks) |

---

## Infrastructure

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Database | PostgreSQL + PostGIS | 15-3.3 | טבלאות, גיאומטריה, חיפוש מרחבי |
| Cache / Pub-Sub | Redis | 7.2.0-v10 | Broadcast (ride updates), chat channels, chat completion, OTP |
| Message Broker | RabbitMQ | 3-management | אירועים (Outbox), תורי משימות (notifications, avatar, scheduled) |
| Runtime | Docker Compose | — | פיתוח: db, redis, rabbitmq, backend (**8000** ל-host), outbox-worker, chat-ws; פרוד מקומי: **frontend** סטטי + **nginx** (80) דרך override + `--profile prod` |

---

## Communication Flow

```
Clients (Web/Mobile)
    │
    ├── HTTP (Docker Compose) ──► nginx:80 → /api/v1/* backend:8000; /ws + /presence/* chat-ws:8081; /* frontend:80
    │
    ├── HTTP REST (מקומי / ישיר) ► backend:8000 (FastAPI)
    │                                    │
    │                                    ├── PostgreSQL (asyncpg)
    │                                    ├── Redis DB 0 (broadcast, cache)
    │                                    ├── Redis DB 1 PUB (chat messages, chat:completion)
    │                                    └── Outbox table ──► outbox-worker
    │
    └── WebSocket /chat ────────► chat-ws:8081 (Go)
                                       │
                                       └── Redis DB 1 SUB (chat:conversation:*, chat:typing:*)

outbox-worker
    ├── Poll outbox_events (PENDING) ──► Publish to RabbitMQ (exchanges: user, ride, booking, tasks, scheduled)
    ├── notifications_queue consumer ──► Send email (Brevo), push (Firebase FCM, **`data` map only** — title/body strings in `data`; UI: toast+chime / SW notification)
    ├── avatar_upload_queue consumer ──► S3 resize, DB update
    ├── scheduled_tasks_queue consumer ──► Reminders, fuel scan, maintenance
    └── Redis DB 1 SUB (chat:completion:*) ──► AI analysis (Groq), save ChatAnalysis, optional outbox
```

---

## Features

- **GPS Tracking**: מיקום נהג ונוסעים בזמן אמת במהלך נסיעה פעילה. נהג: **התחל/סיים נסיעה** מטאב "אני נהג" ב־My Bookings (דורש לפחות הזמנה אחת מאושרת), שידור מיקום ל־POST /bookings/{id}/location; נוסעים מקבלים עדכונים ב־WebSocket /bookings/ws/{id}/location. נוסעים יכולים לשתף מיקום ל־POST /bookings/{id}/passenger-location; נהג מאזין ב־WebSocket /rides/ws/{id}/passengers. ערוצי Redis: `booking_{booking_id}` (מיקום נהג), `ride_{ride_id}:passenger_locations` (מיקום נוסעים). ראה `docs/architecture/REALTIME.md` ו־`docs/architecture/API.md`.
- **Ride preview cache**: תצוגת מקדימה לנסיעה (3 מסלולים) נשמרת ב־Redis 24 שעות; סריאליזציה עם `driver_id` כ־string. תג קבוצה בכרטיסיות (group_name או "ציבורי") מ־RideResponse (כולל group).

---

## Key Patterns

- **Outbox Pattern**: אירועים נכתבים ל-`outbox_events` ב-DB; ה-worker קורא ומפרסם ל-RabbitMQ. מבטיח at-least-once ולא מאבד אירועים.
- **Domain-Driven Design**: כל דומיין (users, rides, bookings, passengers, chat, groups) — model, schema, crud, service.
- **JWT Auth**: Access Token (קצר) + Refresh Token (ארוך, נשמר ב-DB). אותו SECRET_KEY בין backend ל-chat-ws לאימות WebSocket.
- **Cursor-based Pagination**: נסיעות (חיפוש), הודעות צ'אט — `after` / `before` + `limit`, תגובה עם `next_cursor`, `has_more`.
- **Page-based Pagination**: הזמנות שלי — `page`, `limit`, תגובה עם `total`, `has_more`.
- **Pessimistic Locking**: `approve_booking`, `cancel_booking` — שליפת נסיעה עם `SELECT ... FOR UPDATE` כדי למנוע race.
- **Race Condition Protection**: אישור/ביטול הזמנה תחת lock על ה-ride; ביטול מחזיר נסיעה ל-OPEN רק אם לא CANCELLED.

---

## Push notifications (FCM, Web)

- **Outbox → RabbitMQ → notifications consumer** שולח דרך Firebase Admin ל־`users.fcm_token`.
- **פורמט הודעה מהשרת:** רק מפת **`data`** ב־FCM (אין אצלנו שדה `notification` ברמת ה-API של Firebase Admin) — `title` ו־`body` כמחרוזות בתוך `data`, ראה `backend/app/domain/notifications/channels/push/client.py`. זה **לא** אומר שאין UI: יש **חלונית Toast קופצת + צליל** בחזית והתראת מערכת ברקע.
- **דפדפן:** Service Worker (`frontend/public/firebase-messaging-sw.js`) — handler ל־`push` שמפרש את גוף ה־FCM ומציג התראת מערכת כשהאפליקציה לא בחזית.
- **חזית:** `onMessage` ב־`frontend/src/services/fcm.ts` קורא `title`/`body` מ־`payload.data` (ונופל ל־`notification` אם קיים), מציג Toast (`NotificationToast` ב־Layout) + צליל.
- **תיעוד מפורט:** `docs/FCM_SYSTEM_SUMMARY.md`.

---

## Performance

- **ASGI server**: Gunicorn with 4 workers (`uvicorn.workers.UvicornWorker`), bind `0.0.0.0:8000` (production / Docker). Local dev may use uvicorn with `--reload`.
- **Connection Pool** (`backend/app/db/session.py`): `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle` מ-**config** (`DB_POOL_*` ב-`.env`; ברירות מחדל ב-`Settings`), `pool_pre_ping=True`.
- **Indexes**: ראה `docs/DATABASE.md` — כולל 11 ה-indexes מ-migration 004 (rides, bookings, group_members, passenger_requests).
- **Caching**: Redis לפי צורך — TTL וכו' לפי סוג (למשל OTP, broadcast channels).

---

## Observability

### Logging
- Format: JSON (production) / text (development)
- Library: python-json-logger
- Fields: timestamp, level, service, message
- Controlled via: LOG_FORMAT, LOG_LEVEL env vars

### Request Tracing
- Every request gets a unique Request ID (8 chars)
- Returned in response header: X-Request-ID
- Use to trace a specific request across logs

---

## Security

- **JWT**: HS256, `SECRET_KEY` חובה בפרודקשן. Access/Refresh expiry מ-config.
- **CORS**: `CORS_ORIGINS` או `FRONTEND_URL`; ב-DEBUG גם localhost regex.
- **Rate Limiting**: Auth endpoints — חלון שניות + מקסימום בקשות ל-IP (`RATE_LIMIT_AUTH_*`); כולל **`POST /register`** לצד login/refresh וכו’.
- **Password hashing**: bcrypt; חישוב/אימות סיסמה רץ ב-**thread pool** (`run_in_executor`) כדי לא לחסום את ה-event loop.
- **OTP (אימות מייל / איפוס סיסמה)**: קוד אקראי עם **`secrets`**; השוואה עם **`hmac.compare_digest`**; מונה ניסיונות ב-Redis + איפוס בעת הנפקת קוד חדש.
- **HTTPS**: `FORCE_HTTPS_REDIRECT` מאחורי proxy בפרודקשן.
- **Username enumeration (OWASP):** בלוגין מייל/סיסמה, **אותה שגיאה** (`InvalidCredentialsError` / 401) גם כשהאימייל לא קיים ב-DB וגם כשהסיסמה שגויה — כדי שלא יהיה ניתן להבדיל תגובה ולמפות משתמשים. מימוש: `authenticate_and_create_token` ב-`auth/service.py`.

---

## Future Considerations

- **Kafka**: הוחלף ב-RabbitMQ לפשטות בסקלה הנוכחית.
- **Horizontal scaling**: מתוכנן — backend stateless; DB/Redis/RabbitMQ מרכזיים.
