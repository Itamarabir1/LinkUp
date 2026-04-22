# LinkUp — Architecture Overview

תיעוד רמה גבוהה של המערכת. לעדכונים מפורטים: `docs/DATABASE.md`, `docs/API.md`, `docs/EVENTS.md`, `docs/architecture/REALTIME.md`, `docs/DEVELOPMENT.md`. **שגיאות API אחידות (JSON, trace_id, Sentry):** [`docs/ERRORS.md`](docs/ERRORS.md). **להצגת הפרויקט (פיצ’רים, סקייל, טריקים):** `docs/ENGINEERING_HIGHLIGHTS.md`. **מסך אדמין + מפת API:** `ADMIN_DASHBOARD.md` (בשורש).

---

## Services

| Service | Path | Language | Port | Purpose |
|---------|------|----------|------|---------|
| backend | backend/ | Python / FastAPI | 8000 | REST API, auth, rides, bookings, chat, groups, geo, **admin JSON API** |
| notification-worker | backend/ (same image) | Python | — | Outbox -> RabbitMQ, notifications, user refresh events |
| task-worker | backend/ (same image) | Python | — | Avatar tasks, scheduled tasks, scheduled publisher (**replicas=1**) |
| ai-worker | backend/ (same image) | Python | — | Redis chat completion listener + AI analysis |
| email-renderer | email-renderer/ | Node.js / Express / React Email | 3001 | Renders email HTML from template name + props (`POST /render`) |
| chat-ws | chat-ws/ | Go | 8081 | WebSocket server for real-time chat (JWT, Redis Pub/Sub) |
| db | Docker | PostgreSQL 15 + PostGIS | 5432 | Primary data store |
| redis | Docker | Redis Stack 7.2 | 6379 | Single Redis server - DB 0: backend + task/notification infra; DB 1: chat-ws + AI completion + user events |
| rabbitmq | Docker | RabbitMQ 3 + Management | 5672, 15672 | Message broker (events, tasks) |

---

## Infrastructure

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Database | PostgreSQL + PostGIS | 15-3.3 | טבלאות, גיאומטריה, חיפוש מרחבי |
| Cache / Pub-Sub | Redis | 7.2.0-v10 | DB 0: ride per-ride + **rides:list**, cache, OTP, **JWT denylist** (`denylist:{jti}`), **idempotency keys** (`idempotency:request_ride:{user_id}:{key}`); DB 1: chat + **`user:{id}:events`** (דרך `redis_chat_pubsub`), completion, presence |
| Message Broker | RabbitMQ | 3-management | אירועים (Outbox), תורי משימות (notifications, avatar, scheduled) |
| Email rendering | Node.js + Express + React Email | Node 20 | microservice called by backend/worker to render transactional email HTML |
| Runtime | Docker Compose | — | Dev: db, redis, rabbitmq, **migrate** (once), backend (**8000** host), `notification-worker`, `task-worker`, `ai-worker`, chat-ws; local prod: static frontend + nginx (80) with `--profile prod` |
| CDN (אופציונלי) | **Amazon CloudFront** | — | דומיין ציבורי מול אותו bucket S3; מופעל כש־**`CLOUDFRONT_DOMAIN`** מוגדר — URLs יציבים לתמונות (אווטאר/קבוצות); ללא דומיין — presigned GET ישירות ל-S3 |

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
    │                                    ├── Redis DB 1 PUB (chat messages, user:*:events, chat:completion)
    │                                    └── Outbox table ──► notification-worker
    │
    └── WebSocket /chat ────────► chat-ws:8081 (Go)
                                       │
                                       └── Redis DB 1 SUB (chat:conversation:*, chat:typing:*, chat:notification:*, user:*:events)

notification-worker
    ├── Outbox LISTEN/NOTIFY + fallback polling ──► Publish to RabbitMQ (user, ride, booking, tasks, scheduled)
    └── notifications_queue consumer ──► Render email via email-renderer (`POST /render`) ──► Send email/push/user-refresh

task-worker
    ├── avatar_upload_queue consumer ──► S3 resize, DB update
    ├── scheduled_tasks_queue consumer ──► reminders, maintenance, fuel scan
    └── scheduled publisher loop (kept single-replica to avoid duplicate dispatch)

ai-worker
    └── Redis DB 1 SUB (chat:completion:*) ──► AI analysis (Groq), save ChatAnalysis, optional outbox
```

---

## Features

- **GPS Tracking**: מיקום נהג ונוסעים בזמן אמת במהלך נסיעה פעילה. נהג: **התחל/סיים נסיעה** מטאב "אני נהג" ב־My Bookings (דורש לפחות הזמנה אחת מאושרת), שידור מיקום ל־POST /bookings/{id}/location; נוסעים מקבלים עדכונים ב־WebSocket /bookings/ws/{id}/location. נוסעים יכולים לשתף מיקום ל־POST /bookings/{id}/passenger-location; נהג מאזין ב־WebSocket /rides/ws/{id}/passengers. **אימות הרשאות וסטטוס נסיעה** ל־POSTי המיקום — ב־`BookingLocationService.broadcast_driver_location` / `broadcast_passenger_location` ([`location_service.py`](backend/app/domain/bookings/location_service.py); גם ייצוא מ־[`service.py`](backend/app/domain/bookings/service.py)); הראוטר קורא לשירות בלבד. ערוצי Redis: `booking_{booking_id}` (מיקום נהג), `ride_{ride_id}:passenger_locations` (מיקום נוסעים) — שמות מרוכזים ב־`app/infrastructure/redis/keys.py`. **עדכוני סטטוס נסיעה** ללקוח (ערוץ `ride_{ride_id}`): `publish_ride_event` ב־`app/infrastructure/redis/publisher.py`; **רשימת נסיעות** (`rides:list`) נשארת דרך `app/infrastructure/redis/broadcast.py` (Broadcast). **אירועי משתמש** (תחזוקה וכו'): `publish_user_event` → **`redis_chat_pubsub`** על **`REDIS_CHAT_URL`** (DB 1) → ערוץ `user:{user_id}:events` → **chat-ws** נרשם ל-pattern `user:*:events` ומעביר ל־WebSocket של אותו משתמש. **פרונט:** throttle לשידור ~1.5s; `useLocationBroadcast` משתמש ב־`booking_id` של נוסע **מאושר** מתוך רשימת הנוסעים שנטענת עם טאב הנהג (אותו מידע כמו ב־driver-summary); `useUserEventStream` מפרש אירועי משתמש (Zod) על אותו חיבור chat-ws — פירוט ב־`docs/architecture/REALTIME.md`. ראה גם `docs/architecture/API.md`.
- **Ride preview cache**: תצוגת מקדימה לנסיעה (3 מסלולים) נשמרת ב־Redis 24 שעות; סריאליזציה עם `driver_id` כ־string. תג קבוצה בכרטיסיות (group_name או "ציבורי") מ־RideResponse (כולל group).
- **Avatar / Group images (S3)**: העלאה ישירה עם presigned PUT (`/users/me/avatar/upload-url`, `/groups/{id}/upload-image`). אווטאר משתמש: אחרי worker, `avatar_key` מצביע ל-prefix **גרסתי immutable** `avatars/{user_id}/v{version}/` (מחיקת גרסה קודמת רק אחרי commit ל-DB). קריאה: `CLOUDFRONT_DOMAIN` אם מוגדר (URL יציב ל-CDN), אחרת presigned GET ל-S3. קבוצות: מפתח GROUPS/ כמו קודם.
- **Geocode cache (24h)**: תוצאות כתובת→קואורדינטות נשמרות ב־Redis ל־24 שעות כדי לצמצם קריאות חוזרות ל־**Google Geocoding** עבור אותן כתובות. המימוש fail-open כדי לא לחסום flow אם Redis לא זמין.
- **Google Maps — Circuit Breaker**: קריאות ה-API בבקאנד (**Geocoding**, **Directions**, **Distance Matrix**) עטופות במעגלים in-memory נפרדים ב־**`app/infrastructure/geo/circuit_breaker.py`**; כשלונות מצטברים פותחים את המעגל ומונעים קריאות חיצוניות עד התאוששות. מצב המעגלים מוחזר ב־**`GET /api/v1/health`** תחת **`circuit_breakers`** ואינו משפיע על **`status`** הכללי (נקבע רק מ-DB / Redis / RabbitMQ).
- **נוסע — חיפוש לעומת שמירת התראה:** `GET /api/v1/passenger/passengers/search-rides` מחזיר נסיעות פתוחות ב-cursor pagination **בלי** ליצור שורה ב-`passenger_requests`. כדי לקבל מייל/פוש כשיופרסמה נסיעה חדשה שמתאימה למסלול — `POST /api/v1/passenger/passengers/` (`PassengerRequestCreate`) עם `is_notification_active=True` (ברירת מחדל) ואופציונלית `group_id` כשהחיפוש הוא בהקשר קבוצה. **שרשרת אסינכרונית:** Outbox **`ride.created`** (לא `ride.created_for_passengers`) → `notification-worker` → `handle_ride_created` → `find_passengers_for_ride_notification` → אירוע פנימי **`ride.created_for_passengers`** per passenger ב-`notification_handler` (מייל Brevo). אין יצירת booking אוטומטית. פירוט מדויק: `docs/architecture/EVENTS.md` (סעיף Ride) + `docs/ENGINEERING_HIGHLIGHTS.md` §6.4.
- **AI free-text לרכיבה (נוסע + נהג):** endpoint משותף `POST /api/v1/passenger/passengers/ai-parse-search` משרת שני flows: (1) `SearchRides` לנוסע; (2) `CreateRide` לנהג עם constraints מחמירים יותר (`departure_time` עתידי חובה, `departure_date` לבדו לא מספיק), מילוי טופס בלבד וללא auto-submit.
- **Admin (תפעול):** REST תחת **`/api/v1/admin/*`** — רק משתמש עם `users.is_admin`; dependency ב־`app/api/dependencies/admin.py` (`get_current_admin_user`). ראוטר דומיין: `backend/app/domain/admin/router.py` (סטטיסטיקות, בריאות, משתמשים, נסיעות, קבוצות, Outbox, lookup); פעולות רגישות עם לוג **`[admin_audit]`**. במקביל נשאר **SQLAdmin** (`app/admin/setup.py`) לדפדפן ניהול DB קלאסי. **ממשק React** למפעילים: `frontend/src/features/admin/` — מסלולים `/admin`, `/admin/health`, `/admin/users`, `/admin/rides`, `/admin/groups`, `/admin/outbox`, `/admin/lookup` (טעינה עצלה, RTL); **מעטפת דסקטופ בלבד** (ללא drawer/סיידבר מובייל) — שימוש אדמין מכוון לדפדפן; אפליקציית **mobile/** נפרדת. מקור אמת למסך ול־API: **`ADMIN_DASHBOARD.md`**.

---

## Key Patterns

- **Outbox Pattern**: אירועים נכתבים ל-`outbox_events` ב-DB **באותה טרנזקציה** עם השינוי העסקי; ה-worker (`notification-worker`) מפרסם ל-RabbitMQ (LISTEN/NOTIFY + fallback polling). מבטיח **at-least-once** ולא מאבד אירועים אם RabbitMQ זמנית למטה. **דוגמאות routing keys / אירועים:** `ride.created`, `ride.cancelled_by_driver`, `booking.passenger_join_request`, `booking.approved_by_driver`, `booking.rejected_by_driver`, `auth.email_verification`, `auth.password_reset_code`, `user.registered` (מקור אמת מלא: [`docs/architecture/EVENTS.md`](docs/architecture/EVENTS.md)). קוד: [`app/infrastructure/outbox/`](backend/app/infrastructure/outbox/), [`app/domain/events/outbox.py`](backend/app/domain/events/outbox.py).
- **Domain-Driven Design**: כל דומיין (users, rides, bookings, passengers, chat, groups, **admin**, auth, …) — model, schema, crud, service; ראוטרים תחת `backend/app/domain/*/router.py` ונרשמים ב־[`api/v1/api_router.py`](backend/app/api/v1/api_router.py). **רישום מודלי SQLAlchemy:** `import app.db.models` נטען מוקדם כדי לרשום את מודלי הדומיינים שנדרשים לטעינת API/relationships. הוא לא אמור להיתפס כרשימה ממצה של כל מודל אפשרי בריפו (למשל מודלים תשתיתיים כמו outbox). ב־[`alembic/env.py`](backend/alembic/env.py) אותו ייבוא לפני `target_metadata` ל־autogenerate. ב־Ruff: `per-file-ignores` ל־F401 על קבצי registry (`api_router.py`, `app/db/models.py`, `alembic/env.py`, `main_worker.py`) — ראו [`backend/pyproject.toml`](backend/pyproject.toml).
- **Dependency Injection (FastAPI Depends)**: `RideService` ו-`AuthService` נוצרים דרך factories ב-`backend/app/api/dependencies/services.py`, והראוטרים מזריקים אותם עם `Depends(get_ride_service)` / `Depends(get_auth_service)` (במקום singletons גלובליים).
- **JWT Auth**: Access Token (קצר, כולל **`jti`** ייחודי לכל הנפקה) + Refresh Token (ארוך, נשמר ב-DB). **`POST /auth/logout`** (עם Bearer) מנקה refresh ומוסיף את ה-access הנוכחי ל-**Redis denylist** עד פקיעת ה-`exp` (`SETEX denylist:{jti}`); `get_current_user` / `get_current_user_optional` בודקים denylist אחרי פענוח (Redis **fail-open** ב-`is_denied` — אם Redis נופל, לא חוסמים את כל המשתמשים). יצירת טוקן: `create_access_token` ב-`app/core/security.py`; denylist: **`app/infrastructure/redis/client.py`**, logout: **`app/domain/auth/service.py`**, תלות HTTP: **`app/api/dependencies/auth.py`**. אותו SECRET_KEY בין backend ל-chat-ws לאימות WebSocket.
- **WebSocket auth (FastAPI)**: `get_current_user_ws` ב-`app/api/dependencies/auth.py` מאמת **JWT** (`decode_access_token`: חתימה, `exp`, base64 קנוני), בודק `jti` מול Redis denylist (`is_denied`, fail-open), ומחזיר `WsUser` עם `user_id` מה-`sub` — **בלי קריאת DB** בזמן חיבור, כדי לא להעמיס על ה-connection pool תחת עומס. HTTP (`get_current_user`) עדיין טוען `User` מ-DB ובודק גם `is_active`.
- **Cursor-based Pagination**: נסיעות (חיפוש), הודעות צ'אט — `after` / `before` + `limit`, תגובה עם `next_cursor`, `has_more`.
- **Chat read cursor**: `conversation_participants.last_read_message_id` is the source of truth for read receipts. `mark_conversation_read` advances it monotonically; REST returns `partner_read_up_to_message_id`, and `message_read` WS events carry `read_up_to_message_id` so the UI can mark every outgoing message up to that cursor as read.
- **Chat plaintext-only input (XSS hardening)**: `MessageCreate.reject_html` in [`backend/app/domain/chat/schema.py`](backend/app/domain/chat/schema.py) rejects bodies containing HTML tags (`<...>`). This blocks stored HTML payloads at API entry and keeps chat content policy as plain text.
- **Page-based Pagination**: הזמנות שלי — `page`, `limit`, תגובה עם `total`, `has_more`.
- **Pessimistic Locking**: `approve_booking`, `cancel_booking` — שליפת נסיעה עם `SELECT ... FOR UPDATE` כדי למנוע race. **שגיאות טרנזקציה:** `approve_booking`, `reject_booking`, `cancel_booking` — `rollback` גם על `Exception` לא צפוי אחרי `flush`, עם לוג — עקבי עם `request_to_join`.
- **Race Condition Protection**: אישור/ביטול הזמנה תחת lock על ה-ride; ביטול מחזיר נסיעה ל-OPEN רק אם לא CANCELLED.
- **Async SQLAlchemy 2.0 core domains**: passenger/bookings/rides core flows עברו ל־`AsyncSession` ו־`select/execute`.
  - **Bookings** async-only (ללא `db.run_sync`) ומשתמשים ב־`select(...).with_for_update()` לנעילות שורה.
  - **Workers / notifications:** `find_passengers_for_ride_notification`, טעינת הזמנות ב־`handle_ride_cancelled_by_driver` ([`notification_tasks.py`](backend/app/workers/tasks/notification_tasks.py)) וכו' — **async** (`await db.execute(select(...))`). אין `Session.run_sync` בקוד האפליקציה; `run_sync` נשאר רק ב־Alembic (`env.py`) לצורך מיגרציות.
  - **ביטול נסיעה — התראות:** רק הזמנות במצב **PENDING** או **CONFIRMED** מקבלות `ride.cancelled_by_driver` (לא הזמנות שכבר **CANCELLED**).
- **Chat inbox read path (anti N+1):** `list_my_conversations` משתמש ב-`get_inbox_aggregates` כדי להביא `last_message` + `has_unread` בבאצ' קבוע, ללא await DB פר-שיחה.
- **תזכורות**: אין עוד `reminder_sent` על `rides`/`bookings` ב-ORM או ב-API ציבורי (מיגרציה **008**); תזמון בשכבת `scheduled_notifications` + `ReminderScheduler` + notification handler; סימון נשלח ב-`sent_at`.
- **תחזוקת סטטוסים (maintenance)**: `MaintenanceCRUD` מחזיר `PendingUserEvent` עם RETURNING; אחרי `commit` מוצלח, `MaintenanceService` מפרסם `publish_user_event` (מוגן ב-`USER_EVENTS_ENABLED` ב-config).
- **שגיאות API מרוכזות**: תת־מחלקות של `LinkUpError` לפי דומיין ב־`app/core/exceptions/`; ב־`main.py` handlers גלובליים ל־Pydantic (`RequestValidationError` → 422), `IntegrityError` / `SQLAlchemyError`, ו־`LinkUpError`. פורמט JSON, Sentry, פרונט ו-chat-ws: [`docs/ERRORS.md`](docs/ERRORS.md).
- **Idempotency-Key (Stripe-style)** ל־**`POST /passenger/passengers/request-ride-from-search`**: כותרת אופציונלית **`Idempotency-Key`** + Redis (**`SET NX`** ל-claim, fingerprint SHA-256 לגוף קנוני) — מניע כפילות בקשות הצטרפות בלחיצה כפולה / retry רשת; נשמר ב-Redis רק **תשובת 201 מוצלחת** (TTL ~5 דק׳); שגיאות עסקיות מוחקות את הנעילה לאפשר ניסוי חוזר; Redis לא זמין → **fail-open**. **קוד:** `app/domain/passengers/router.py` (עזרי fingerprint/מפתח ב־[`ride_join_idempotency.py`](backend/app/domain/passengers/ride_join_idempotency.py)), `app/infrastructure/redis/client.py`. **פרונט:** `frontend/src/api/passengers.ts`, **`useJoinRide`** ([`useJoinRide.ts`](frontend/src/pages/SearchRides/useJoinRide.ts)) נקרא מ־**`useSearchRides`** — **`idempotencyKeyRef`**. פירוט: **`docs/ENGINEERING_HIGHLIGHTS.md` סעיף 7ה / 0א**, **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §19**.

---

## Push notifications (FCM, Web)

- **Outbox → RabbitMQ → notifications consumer** שולח דרך Firebase Admin ל־`users.fcm_token`.
- **פורמט הודעה מהשרת:** רק מפת **`data`** ב־FCM (אין אצלנו שדה `notification` ברמת ה-API של Firebase Admin) — `title` ו־`body` כמחרוזות בתוך `data`, ראה `backend/app/domain/notifications/channels/push/client.py`. זה **לא** אומר שאין UI: יש **חלונית Toast קופצת + צליל** בחזית והתראת מערכת ברקע.
- **דפדפן:** Service Worker (`frontend/public/firebase-messaging-sw.js`) — handler ל־`push` שמפרש את גוף ה־FCM ומציג התראת מערכת כשהאפליקציה לא בחזית.
- **חזית:** `onMessage` ב־`frontend/src/services/fcm.ts` קורא `title`/`body` מ־`payload.data` (ונופל ל־`notification` אם קיים), מציג Toast (`NotificationToast` ב־`App.tsx`) + צליל. **מחזור חיים:** אחרי login / Google / טעינת סשן — אם `Notification.permission === 'granted'` מופעל `initFCM()` מ־[`AuthContext`](frontend/src/context/AuthContext.tsx); ב־logout — לפני ביטול סשן: `PATCH /users/fcm-token` עם `fcm_token: null`, `cleanupFCM()`, ואז `logout` + ניקוי טוקנים מקומית. תפריט הפרופיל: "הפעל התראות" קורא `initFCM()` מ־[`useLayoutShell`](frontend/src/components/Layout/useLayoutShell.ts).
- **תיעוד מפורט:** `docs/FCM_SYSTEM_SUMMARY.md`.

---

## Email rendering (React Email)

- **Renderer service:** `email-renderer` (Node.js + Express) exposes:
  - `GET /health` — health + template list
  - `POST /render` — input `{ template, props }`, output `{ html }`
- **Backend integration:** [`backend/app/domain/notifications/channels/email/renderer.py`](backend/app/domain/notifications/channels/email/renderer.py) now delegates rendering to the service via `EMAIL_RENDERER_URL`.
- **Template contract:** backend [`EMAIL_MAP`](backend/app/domain/notifications/config/templates_map/email_conf.py) maps events to **PascalCase** template names (e.g. `BookingApproved`, `VerifyEmail`).
- **Fail-fast safety net:** renderer validates mapped templates at startup via [`emailMapKeys.ts`](email-renderer/src/emails/emailMapKeys.ts) + [`registry.ts`](email-renderer/src/emails/registry.ts); missing template crashes startup instead of failing at send-time.

---

## Frontend — i18n, לוקאליזציה ושגיאות (ווב)

- **שפות:** עברית ואנגלית דרך **i18next**; קבצי תרגום תחת `frontend/src/i18n/locales/{he,en}/`.
- **כיוון ופונטים:** `LangContext` מעדכן `document.documentElement.lang` / `dir` ואת משתנה ה-CSS **`--font-primary`** לפי שפה (RTL + Heebo לעברית; LTR + DM Sans לאנגלית). ב־**CSS Modules** מעדיפים `font-family: var(--font-primary)` ו־`var(--font-numeric)` לעקביות; **`LangToggle`** נשאר עם פונט מונוספי נפרד לווידג'ט.
- **תאריכים ושעות:** פונקציות מרוכזות ב־`frontend/src/utils/date.ts` עם **`getLocale()`** הנגזר מ־`i18n.language` (לא עריכת `he-IL` קשיחה ברוב המסכים).
- **הודעות שגיאה ב־API (fallback):** מחוץ לרכיבים, טקסט fallback ל־`getApiErrorMessage` מגיע מ־**`apiErr('err_*')`** ב־`frontend/src/utils/i18nError.ts` (מפתחות ב־`common.json`), כדי שלא יישארו מחרוזות עברית קשיחות ב-hooks.
- **תיעוד החלטות:** `docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` — סעיפים 10–12.

---

## In-app notifications (פיד התראות בווב)

- **שרת:** WebSocket **`GET /api/v1/notifications/ws?token=JWT`** — `notification_streamer.stream_user_notifications` + Redis Pub/Sub (ערוץ פנימי `user_{user_id}`). אימות JWT בלבד ב-handshake (`get_current_user_ws`) — ללא DB בזמן החיבור; פירוט ב־[`docs/architecture/REALTIME.md`](docs/architecture/REALTIME.md).
- **פרונט:** `ChatContext` מרכיב **`useChatNotificationsWebSocket`** מעל **`useReconnectingWebSocket`**; ב־**`onOpen`** (כולל אחרי reconnect) — רענון פיד התראות, טעינת unread מחדש, ודispatch לאירוע מותאם **`linkup-notifications-refresh`** כדי שמסכים יסתנכרנו. **`useChatNotificationsFeed`** מריץ **polling** ל־REST כל **~5 דקות** כגיבוי כשה-WS לא זמין או לא יציב.

---

## Performance

- **ASGI server (Docker Compose)**: `backend/entrypoint.sh` מריץ `uvicorn` עם `--workers` לפי **`UVICORN_WORKERS`** ב-`backend/.env` (ברירת מחדל **1** אם חסר; ראו `.env.example`: **4**). **מיגרציות** רצות בשירות נפרד **`migrate`** לפני עליית ה-backend. **Healthcheck** על המיכל: `GET /api/v1/health`. **פיתוח לוקאלי** (ללא Docker): בדרך כלל `uvicorn ... --reload` — תהליך יחיד; מיגרציה ידנית (`alembic upgrade head`) לפני הרצה.
- **Connection Pool** (`backend/app/db/session.py`): `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle` מ-**config** (`DB_POOL_*` ב-`.env`; ברירות מחדל ב-`Settings`), `pool_pre_ping=True`.
- **Indexes**: ראה `docs/DATABASE.md` — כולל אינדקסי בסיס ממיגרציה 004 ועוד אינדקסים משלימים מקריאות production חמות (כולל `idx_bookings_request_id`, `idx_messages_sender_id`).
- **Caching**: Redis לפי צורך — TTL וכו' לפי סוג (למשל OTP, broadcast channels).
- **My Bookings — קריאות מאוגדות**: `GET /bookings/driver-summary` ו־`GET /bookings/passenger-summary` ממומשים ב־**`BookingReadsService`** ([`booking_reads_service.py`](backend/app/domain/bookings/booking_reads_service.py)) — שאילתת DB אחת לכל מסך (ראו `bookings/crud.py`: `joinedload` + `with_loader_criteria` על הזמנות pending/confirmed לנהג), במקום סדרת קריאות per-ride. בפרונט יש שכבת mapping ייעודית (`frontend/src/pages/MyBookings/myBookings.mappers.ts`) שממירה DTOs ל-view-model של UI — פירוט ב־`docs/architecture/DATABASE.md` ו־`docs/architecture/API.md`.
- **Chat inbox — קריאות מאוגדות (N+1 fix)**: `list_my_conversations` ([`chat/service.py`](backend/app/domain/chat/service.py)) הריצה `get_last_message` + `has_unread_messages` לכל שיחה בנפרד (~3N DB round-trips). הוחלפה ב-**`get_inbox_aggregates`** ([`chat/crud.py`](backend/app/domain/chat/crud.py)): שלוש `func.max` aggregate queries על כלל השיחות ומיזוג בזיכרון — **4 קריאות קבועות** ללא תלות בגודל ה-inbox.

---

## Observability

### Logging (structured + correlation)
- **Library:** **structlog** — `JSONRenderer` בפרודקשן (`LOG_FORMAT=json`), `ConsoleRenderer` צבעוני בפיתוח (`LOG_FORMAT=text`). הגדרה ב-[`app/core/logging.py`](backend/app/core/logging.py) (`setup_logging`): processors כוללים `request_id` מ-**ContextVar** (`request_id_ctx`).
- **Correlation ID:** [`RequestIDMiddleware`](backend/app/main.py) ב-[`main.py`](backend/app/main.py) מקצה **8 תווים** מ-UUID לכל בקשה, שומר ב-`request.state.request_id`, מעדכן את ה-ContextVar, ומחזיר כותרת **`X-Request-ID`** בתגובה. `RequestIDFilter` מחבר stdlib logging ל-structlog כך שכל שורה נשאבת לאותה בקשה.
- **שגיאות API:** `trace_id` / `request_id` מיושרים ל-handlers — ראו [`docs/ERRORS.md`](docs/ERRORS.md).
- **משתני סביבה:** `LOG_FORMAT`, `LOG_LEVEL`.

### Request Tracing
- מזהה ייחודי קצר (8 תווים) לכל בקשה HTTP; כותרת תגובה **`X-Request-ID`**; חיפוש בלוגים לפי אותו מזהה.

### Health endpoint וניטור
- **Current:** `GET /api/v1/health` (DB, Redis, RabbitMQ + `circuit_breakers` אינפורמטיבי) + **structlog** + **`X-Request-ID`** (ראו לעיל).
- **Sentry (פעיל):** `sentry_sdk.init()` ב-[`app/core/logging.py`](backend/app/core/logging.py) (`setup_logging`) — מופעל כש-`SENTRY_DSN` מוגדר בסביבה; integrations: `FastApiIntegration`, `SqlalchemyIntegration`, `RedisIntegration`; `traces_sample_rate=0.1`. `capture_exception` על 5xx בלבד ב-[`handlers.py`](backend/app/core/exceptions/handlers.py) (מניעת רעש מ-4xx עסקיים). פרונט: `Sentry.init()` ב-`main.tsx` (guard: `PROD + VITE_SENTRY_DSN`); `captureException` ב-axios interceptor (5xx), `ChatErrorBoundary`, `RouteErrorBoundary`.
- **Prometheus + Grafana (פעיל, profile `monitoring`):** backend חושף `GET /metrics` דרך `prometheus-fastapi-instrumentator` (`Instrumentator().instrument(app).expose(...)` ב-`main.py`); ב-Compose נוספו שירותי `prometheus` ו-`grafana` תחת `profiles: ["monitoring"]`, עם קונפיגים ב-`monitoring/prometheus.yml` ו-`monitoring/grafana/provisioning/**`.

---

## Security

- **JWT**: HS256, `SECRET_KEY` חובה בפרודקשן. Access/Refresh expiry מ-config. **Access:** claim **`jti`** + **Redis denylist** לאחר logout — ביטול מיידי של אותו access token (במקביל לניקוי refresh ב-DB).
- **API docs exposure**: Swagger/ReDoc/OpenAPI נשלטים דרך `API_DOCS_ENABLED` ב-`Settings`; ברירת מחדל `False` כך שבפרודקשן `/docs`, `/redoc`, `/openapi.json` כבויים אלא אם הודלקו במפורש (למשל staging פנימי).
- **WebSocket (backend)**: אימות ב-`get_current_user_ws` מבוסס JWT בלבד — אין בדיקת `is_active` בזמן ה-handshake (בחירה מודעת לצמצום עומס DB בזמן חיבור). עם זאת, בדיקת **Redis denylist (`denylist:{jti}`)** נוספה ומיושרת ל-HTTP auth: token שבוטל ב-logout נחסם גם ב-WS handshake (עם fail-open אם Redis לא זמין).
- **CORS**: `CORS_ORIGINS` או `FRONTEND_URL`; ב-DEBUG גם localhost regex.
- **Rate Limiting**: Auth endpoints — חלון שניות + מקסימום בקשות ל-IP (`RATE_LIMIT_AUTH_*`); כולל **`POST /register`** לצד login/refresh וכו’. Chat message endpoint (`POST /chat/conversations/{conversation_id}/messages`) מוגבל פר-משתמש ל-30 הודעות לדקה (`ratelimit:chat:{user_id}`), עם fail-open אם Redis לא זמין.
- **Password hashing**: bcrypt; חישוב/אימות סיסמה רץ ב-**thread pool** (`run_in_executor`) כדי לא לחסום את ה-event loop.
- **OTP (אימות מייל / איפוס סיסמה)**: קוד אקראי עם **`secrets`**; השוואה עם **`hmac.compare_digest`**; מונה ניסיונות ב-Redis + איפוס בעת הנפקת קוד חדש.
- **HTTPS**: `FORCE_HTTPS_REDIRECT` מאחורי proxy בפרודקשן.
- **Username enumeration (OWASP):** בלוגין מייל/סיסמה, **אותה שגיאה** (`InvalidCredentialsError` / 401) גם כשהאימייל לא קיים ב-DB וגם כשהסיסמה שגויה — כדי שלא יהיה ניתן להבדיל תגובה ולמפות משתמשים. מימוש: `authenticate_and_create_token` ב-`auth/service.py`.

---

## בדיקות, עומס ואיכות

- **Backend:** `pytest` תחת `backend/tests/` (auth, JWT, וכו’); ב-CI שירות Postgres, משתנה סביבה **`DATABASE_URL` ברמת ה-job** (אותו ערך ל־**Alembic** ול־**pytest** דרך `Settings` + `conftest`), ובסדר ריצה: **Ruff check** → **Ruff format --check** → **`alembic upgrade head`** → **pytest** (`backend-ci.yml`).
- **Config / env:** ב־`app/core/config.py`, `DATABASE_URL` ו־`REDIS_URL` מהסביבה נטענים לשדות `*_RAW` באמצעות **`validation_alias=AliasChoices(...)`** (pydantic-settings) — לא `json_schema_extra`; כך Alembic (`settings.DATABASE_URL`) והאפליקציה רואים את אותו override כמו ב-CI.
- **Broadcast רשימת נסיעות:** שם ערוץ Redis **`rides:list`** מרוכז ב־`app/infrastructure/redis/keys.py` (`RIDES_LIST_CHANNEL`); שירות הנסיעות מפרסם עדכוני רשימה דרך `broadcast.publish` (תשתית). אירועי נסיעה per-ride ואירועי משתמש per-user יוצאים דרך **`app/infrastructure/redis/publisher.py`**.
- **Frontend:** Vitest (`npm run test` מתוך `frontend/`) — `utils`, `context`, רכיבים, MessageThread; ב-CI — ESLint + build (כולל `tsc`).
- **chat-ws:** `go build` / `go vet` ב־`chat-ws-ci.yml`.
- **עומס (k6):** סקריפטים מאורגנים תחת `backend/k6/scripts/` (auth/rides/users/groups/chat/geo/ws), עם wrappers תואמים לאחור ב־`backend/load_test*.js`. אימות זרימות ליבה תחת עומס מקבילי (executor ל-bcrypt, pool, rate limit, outbox). דורש הכנת סביבה (ראו `docs/architecture/DEVELOPMENT.md`, `backend/README.md`, `docs/ENGINEERING_HIGHLIGHTS.md` סעיף 7ג).
- **אימות טלפון:** ספריית `phonenumbers` **נעולה ל־`8.13.48`** ב־`backend/pyproject.toml` / `uv.lock` ליציבות מספרים ישראליים.

---

## Future Considerations

- **Kafka**: הוחלף ב-RabbitMQ לפשטות בסקלה הנוכחית.
- **Horizontal scaling**: מתוכנן — backend stateless; DB/Redis/RabbitMQ מרכזיים.
- **PgBouncer (מתוכנן, לא ממומש):** pooler בין האפליקציה ל-PostgreSQL — רלוונטי בעיקר כשעולים ל-**10+ מופעי API** / פריסה serverless-ית, כדי לרכז אלפי חיבורי לקוח לפחות חיבורי DB פיזיים. **מצב נוכחי:** SQLAlchemy async pool (`DB_POOL_*`) + `UVICORN_WORKERS` (למשל 4 workers × pool) — Postgres סביר עד מאות חיבורים לפי tuning; אין PgBouncer ב-Compose או ב-K8s כרגע.
- **N+1 / בדיקת שאילתות (המלצה):** No automated EXPLAIN ANALYZE pipeline exists. Manual review recommended on heavy paths (search, matching) using `pg_stat_statements` or Django-style query logging.
