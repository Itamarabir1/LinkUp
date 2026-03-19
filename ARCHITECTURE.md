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
| Runtime | Docker Compose | — | db, redis, rabbitmq, backend, outbox-worker, chat-ws |

---

## Communication Flow

```
Clients (Web/Mobile)
    │
    ├── HTTP REST ──────────────► backend:8000 (FastAPI)
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
    ├── notifications_queue consumer ──► Send email (Brevo), push (Firebase)
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

## Performance

- **ASGI server**: Gunicorn with 4 workers (`uvicorn.workers.UvicornWorker`), bind `0.0.0.0:8000` (production / Docker). Local dev may use uvicorn with `--reload`.
- **Connection Pool** (`backend/app/db/session.py`): `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True` (מונע חיבורים מתים).
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
- **Rate Limiting**: Auth endpoints — חלון שניות + מקסימום בקשות ל-IP (config).
- **HTTPS**: `FORCE_HTTPS_REDIRECT` מאחורי proxy בפרודקשן.

---

## Future Considerations

- **Kafka**: הוחלף ב-RabbitMQ לפשטות בסקלה הנוכחית.
- **Horizontal scaling**: מתוכנן — backend stateless; DB/Redis/RabbitMQ מרכזיים.
