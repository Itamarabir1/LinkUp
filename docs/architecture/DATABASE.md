# Database Architecture

PostgreSQL 15 + PostGIS. מקור: `backend/app/domain/*/model.py`, `backend/alembic/versions/`.

---

## Overview

- **Driver**: asyncpg (`postgresql+asyncpg://`).
- **Connection**: `backend/app/db/session.py` — `get_db()` מחזיר AsyncSession.
- **רשימות נסיעות (נהג / קבוצה):** `get_by_driver_id` / `get_by_group_id` מגבילות ל־**200** שורות במיון `departure_time DESC` (קבוע `_RIDES_HARD_LIMIT` ב־`rides/crud.py`); ראו **`docs/architecture/API.md`** ל־`/rides/me` ו־`/groups/{id}/rides`.
- **מדיה (קשר ל-S3, לא עמודה נפרדת):** שדות `avatar_key` ב-`users` / `groups` מחזיקים prefix או מפתח אובייקט ב-bucket; ה-API בונה URL ציבורי — עם **`CLOUDFRONT_DOMAIN`** (ראו `app/core/config.py`, `app/infrastructure/s3/service.py`) או presigned. פירוט תהליך אווטאר גרסתי: `ARCHITECTURE.md` (Features), `docs/ENGINEERING_HIGHLIGHTS.md` (סעיף 12).

---

## Connection Pool

מקור: `backend/app/db/session.py` — ערכים מ-`app.core.config.settings` (ניתן לעקוף ב-`.env`).  
ב-runtime, השירותים מתחברים ל-Postgres דרך `pgbouncer` (transaction pooling); מיגרציות (`migrate`) נשארות direct ל-`db`.

| Parameter | Env / default | הערות |
|-----------|----------------|--------|
| pool_size | `DB_POOL_SIZE` (default 5) | חיבורים קבועים במאגר |
| max_overflow | `DB_MAX_OVERFLOW` (default 10) | חיבורים נוספים מעבר ל-pool_size |
| pool_timeout | `DB_POOL_TIMEOUT` (default 30s) | המתנה לחיבור פנוי מהמאגר |
| pool_recycle | `DB_POOL_RECYCLE` (default 1800s) | מחזור חיבורים (למניעת חיבורים “מתים” אצל שרת ה-DB) |
| pool_pre_ping | True (קוד) | בודק חיבור לפני שימוש (מונע חיבורים מתים) |
| connect_args.statement_cache_size | 0 (קוד) | תאימות asyncpg עם PgBouncer במצב transaction pooling |
| statement_timeout (layered) | `DB_STATEMENT_TIMEOUT_MS` ב-`connect_args.server_settings` (`app/db/session.py`) + migration **`017_set_statement_timeout`** ceiling | **ערך אופרטיבי ברמת session** מהאפליקציה (תלוי `.env`, ברירת מחדל 30s); **ceiling דיפנסיבי קשיח של 60s** ברמת role (literal — דטרמיניסטי בלי תלות runtime). הגבלת זמן לשאילתה ברמת Postgres לפני Gunicorn timeout. |

### PgBouncer (runtime layer)

| Parameter | Value | הערות |
|-----------|-------|--------|
| pool_mode | transaction | ברירת מחדל מומלצת ל-API workloads |
| max_client_conn | 400 | קיבולת חיבורי לקוח ל-pooler |
| default_pool_size | 20 | חיבורים פיזיים עיקריים ל-Postgres לכל DB/user |
| reserve_pool_size | 5 | headroom בזמן burst |
| server_idle_timeout | 30 | שחרור חיבורים לא פעילים |

קבצי קונפיג: `infrastructure/pgbouncer/pgbouncer.ini`, `infrastructure/pgbouncer/userlist.txt.template`, `infrastructure/pgbouncer/entrypoint.sh` (הקובץ `userlist.txt` נוצר **בתוך הקונטיינר** בזמן startup מ־`POSTGRES_USER`/`POSTGRES_PASSWORD`/`PGBOUNCER_ADMIN_PASSWORD`; לא נשמר ב-git ולא נוצר ב-CI על host).

### Redis topology (HA)

- Compose runtime: `redis-primary` (master), `redis-replica` (replication), `redis-sentinel` (failover detection).
- Python clients (`RedisClient`, `RedisChatPubSub`, `RedisBroadcast`) משתמשים ב-`redis.asyncio.Sentinel` כש-`REDIS_SENTINEL_HOST` מוגדר; אחרת fallback ל-`REDIS_URL`.
- DB split נשאר: **DB 0** ל-cache/rate-limit/denylist/idempotency, **DB 1** לצ'אט/pubsub.

---

## Tables

### users

משתמשים — נהגים ונוסעים. אימות: סיסמה, Google OAuth (google_id).

| שדה | טיפוס | הערות |
|-----|--------|--------|
| user_id | UUID PK | |
| full_name | VARCHAR(100) NOT NULL | |
| phone_number | VARCHAR(20) UNIQUE NOT NULL | index |
| email | VARCHAR(255) UNIQUE | index |
| hashed_password | VARCHAR(255) NOT NULL | |
| is_verified | BOOLEAN DEFAULT FALSE | |
| google_id | VARCHAR(255) | קישור ל-Google |
| is_active | BOOLEAN DEFAULT TRUE | |
| is_admin | BOOLEAN DEFAULT FALSE | |
| avatar_key | VARCHAR(255) | מפתח/-prefix S3 לתמונות אווטאר (מיגרציה 002: `avatar_url` → `avatar_key`). **מומלץ בזרימה הנוכחית:** prefix גרסתי **`avatars/{user_id}/v{version}/`** אחרי worker; ערכים ישנים ללא `v{version}/` עדיין תקפים עד העלאה מחדש. |
| fcm_token | TEXT | Firebase push |
| refresh_token | TEXT | JWT refresh |
| last_location | GEOGRAPHY(POINT) | PostGIS |
| last_login | TIMESTAMPTZ | התחברות אחרונה |
| last_active_at | TIMESTAMPTZ | פעילות אחרונה (צ'אט / PATCH last-seen מ-chat-ws); אינדקס; מיגרציה **007** |
| stripe_customer_id | VARCHAR(255) | מזהה לקוח ב-Stripe; אינדקס; מיגרציה **013** |
| is_premium | BOOLEAN DEFAULT FALSE | cache של סטטוס חיוב; מקור אמת בטבלת `payments`; אינדקס; מיגרציה **013** |
| premium_since | TIMESTAMPTZ | תאריך מעבר לפרימיום; מיגרציה **013** |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### payments

טבלת חיובים — מקור אמת לתשלומי Stripe.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| payment_id | UUID PK | |
| user_id | UUID FK users NOT NULL | index (`idx_payments_user_id`) |
| stripe_payment_intent_id | VARCHAR(255) UNIQUE | מזהה תשלום סופי ב-Stripe |
| stripe_session_id | VARCHAR(255) UNIQUE | מזהה Checkout Session |
| stripe_event_id | VARCHAR(255) UNIQUE | idempotency ברמת webhook event |
| amount | NUMERIC(10,2) NOT NULL | סכום בפורמט דצימלי |
| currency | VARCHAR(10) NOT NULL DEFAULT `ils` | מנורמל lowercase |
| status | `payment_status_enum` NOT NULL DEFAULT `pending` | pending/succeeded/failed/canceled; index (`idx_payments_status`). מיגרציה **015** (billing): אינדקס חלקי **`idx_payments_status_created`** על `(status, created_at) WHERE status = 'pending'` — מאיץ את סריקת תשלומים תקועים ל-reconciler. |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

מעברי סטטוס אסורים (למשל succeeded → failed) נחסמים בדומיין ע"י **`validate_transition`** (**`PaymentTransitionError`** / **`ILLEGAL_PAYMENT_TRANSITION`**) ב־`app/domain/billing/state_machine.py`.

### idempotency_keys (billing checkout)

טבלה ל**אידמפוטנטיות דרוכת DB** ל־`POST /billing/checkout` (Stripe-style בתשובת השרת השמורה, לא Redis).

| שדה | טיפוס | הערות |
|-----|--------|--------|
| id | UUID PK | |
| client_key | VARCHAR(128) | ערך הכותרת **`X-Idempotency-Key`** |
| user_id | UUID FK users | |
| endpoint | VARCHAR(64) | לדוגמה נתיב endpoint לזיהוי |
| request_fingerprint | VARCHAR(64) | SHA-256 על פרמטרים קנוניים |
| response_body | JSONB | גוף התשובה הממומש |
| status_code | INTEGER | קוד HTTP שנשמר |
| expires_at | TIMESTAMPTZ | ניקוי אוטומטי + job ב-reconciler |
| created_at | TIMESTAMPTZ | |

**אילוץ:** `UNIQUE (user_id, client_key, endpoint)`. **אינדקס:** `idx_idempotency_expires_at` על `expires_at`.

### groups

קבוצות — נהגים שמזמינים טרמפים בתוך קבוצה.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| group_id | UUID PK | |
| name | VARCHAR(255) NOT NULL | |
| invite_code | VARCHAR(64) UNIQUE NOT NULL | index |
| admin_id | UUID FK users NOT NULL | |
| is_active | BOOLEAN DEFAULT TRUE | |
| max_members | INTEGER | |
| invite_expires_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| avatar_key | VARCHAR(255) | (003) prefix או מפתח S3 לתמונת קבוצה; בניית URL כמו ב־users (CloudFront או presigned) — `app/infrastructure/s3/service.py` |
| description | VARCHAR(500) | (003) |

**יצירת `invite_code`:** Base62 (8 תווים), `flush` + retry על **`IntegrityError`** ייחודי ל־`invite_code`; אחרי ניסיונות חוזרים — `INVITE_CODE_GENERATION_FAILED` — [`app/domain/groups/crud.py`](../../backend/app/domain/groups/crud.py).

### group_members

חברות בקבוצה.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| id | UUID PK | |
| group_id | UUID FK groups NOT NULL | index (004) |
| user_id | UUID FK users NOT NULL | index (004) |
| role | VARCHAR(20) DEFAULT 'member' | |
| joined_at | TIMESTAMPTZ | |
| UNIQUE(group_id, user_id) | | |

### rides

נסיעות שהנהג מציע.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| ride_id | UUID PK | |
| driver_id | UUID FK users NOT NULL | btree מורכב עם `departure_time` — **018** (`idx_rides_driver_departure`; הוסר `idx_rides_driver_id` מ־**004**) |
| group_id | UUID FK groups | btree מורכב חלקי עם `departure_time` — **018** (`idx_rides_group_departure`; הוסר `idx_rides_group_id` מ־**004**), nullable |
| departure_time | TIMESTAMPTZ NOT NULL | |
| estimated_arrival_time | TIMESTAMPTZ | |
| origin_name, destination_name | VARCHAR(255) | |
| origin_geom, destination_geom | GEOGRAPHY(POINT) NOT NULL | |
| route_coords | GEOGRAPHY(LINESTRING) | |
| route_summary | VARCHAR(255) | |
| distance_km, duration_min | NUMERIC | |
| available_seats | INTEGER NOT NULL DEFAULT 4 | |
| price | NUMERIC DEFAULT 0 | |
| status | ride_status ENUM NOT NULL | open, full, **active**, completed, cancelled — index (004). active = נסיעה בתנועה (נהג התחיל/יסיים; שידור GPS). |
| created_at, updated_at | TIMESTAMPTZ | |

### passenger_requests

בקשות נוסע לחיפוש טרמף ("הסוכן החכם").

| שדה | טיפוס | הערות |
|-----|--------|--------|
| request_id | UUID PK | |
| passenger_id | UUID FK users NOT NULL | index (004) |
| group_id | UUID FK groups | |
| num_passengers | INTEGER NOT NULL | |
| pickup_name, destination_name | VARCHAR(255) | |
| pickup_geom, destination_geom | GEOGRAPHY(POINT) | |
| requested_departure_time | TIMESTAMPTZ NOT NULL | |
| search_radius_meters | INTEGER DEFAULT 500 | |
| distance_km, duration_min | NUMERIC | |
| status | passenger_request_status ENUM | index (composite עם time במודל) |
| is_notification_active | BOOLEAN | |
| created_at, updated_at | TIMESTAMPTZ | |

### bookings

הזמנת מקום בנסיעה — צומת בין נוסע לנסיעה.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| booking_id | UUID PK | |
| ride_id | UUID FK rides NOT NULL | index (004) |
| passenger_id | UUID FK users NOT NULL | index (004) |
| request_id | UUID FK passenger_requests | |
| num_seats | INTEGER NOT NULL | |
| pickup_name, pickup_point, pickup_time | VARCHAR/GEOGRAPHY/TIMESTAMPTZ | |
| status | booking_status ENUM NOT NULL | pending_approval, confirmed, rejected, cancelled, completed, **en_route**, **arrived**, **trip_in_progress** (השלוש האחרונים — מיגרציה **019**; מחזור נסיעה; אינדקס 004) |
| created_at, updated_at | TIMESTAMPTZ | |
| UNIQUE(ride_id, passenger_id) | | |

**קריאות מאוגדות (מסך “הזמנות שלי”):**

- **נהג — פעיל:** `GET /bookings/driver-summary/active` — [`get_driver_active_rides`](../../backend/app/domain/bookings/crud.py): רק נסיעות **`open` / `full` / `active`**; `with_loader_criteria` כולל גם סטטוסי **מחזור נסיעה** (`en_route`, `arrived`, `trip_in_progress`); מיון `departure_time ASC`; **`LIMIT 200`**.
- **נהג — היסטוריה:** `GET /bookings/driver-summary/history` — [`get_driver_history_rides`](../../backend/app/domain/bookings/crud.py): נסיעות **`completed` / `cancelled`**; אותם joins; **`with_loader_criteria`** על **confirmed, cancelled, completed, rejected** כדי שיופיעו נוסעים גם אחרי סיום/ביטול; מיון **`departure_time DESC, ride_id DESC`**; דפדוף `limit+1` + תנאי קורסור על `(departure_time, ride_id)`.
- **נוסע — פעיל:** `GET /bookings/passenger-summary/active` — [`get_passenger_active_bookings`](../../backend/app/domain/bookings/crud.py): הזמנות פעילות (כולל מחזור נסיעה); **`LIMIT 200`**.
- **נוסע — היסטוריה:** `GET /bookings/passenger-summary/history` — [`get_passenger_history_bookings`](../../backend/app/domain/bookings/crud.py): סטטוסים טרמינליים; מיון **`Ride.departure_time DESC, booking_id DESC`**; דפדוף `limit+1` + קורסור.
- **קוד קורסור משותף (UTC):** [`core/pagination/cursor.py`](../../backend/app/core/pagination/cursor.py) משמש bookings/chat/rides/passengers עם payload אטום ו-normalization ל-UTC.

### conversations

שיחת 1:1 בין שני משתמשים. user_id_1 < user_id_2 תמיד.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| conversation_id | UUID PK | |
| user_id_1, user_id_2 | UUID FK users NOT NULL | |
| created_at | TIMESTAMPTZ | |
| UNIQUE(user_id_1, user_id_2) | | |

### messages

הודעות בתוך שיחה.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| message_id | BIGSERIAL PK | |
| conversation_id | UUID FK conversations NOT NULL | |
| sender_id | UUID FK users NOT NULL | |
| body | TEXT NOT NULL | |
| created_at | TIMESTAMPTZ | |

### chat_analysis

ניתוח AI של שיחה (Groq). שורה אחת לשיחה.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| analysis_id | BIGSERIAL PK | |
| conversation_id | UUID FK conversations UNIQUE | |
| driver_name, passenger_name, pickup_location, meeting_time | TEXT | |
| summary_hebrew | TEXT | |
| analysis_json | JSONB | |
| created_at | TIMESTAMPTZ | |

### outbox_events

Outbox — אירועים שמחכים לפרסום ל-RabbitMQ.

| שדה | טיפוס | הערות |
|-----|--------|--------|
| id | UUID PK | |
| event_name | VARCHAR(100) NOT NULL | index |
| payload | JSONB NOT NULL | |
| targets | VARCHAR[] NOT NULL | |
| metadata | JSONB | |
| status | VARCHAR(20) DEFAULT 'PENDING' | index |
| retry_count | INTEGER DEFAULT 0 | |
| last_error | TEXT | |
| created_at | TIMESTAMPTZ | |
| processed_at | TIMESTAMPTZ | |

### scheduled_notifications

תזמון תזכורות (נוסע/נהג) והחלפת דגל `reminder_sent` שהוסר מ-rides/bookings (מיגרציה **008**).

| שדה | טיפוס | הערות |
|-----|--------|--------|
| id | UUID PK | |
| ride_id | UUID FK rides | nullable אם רלוונטי |
| user_id | UUID FK users NOT NULL | |
| type | VARCHAR(50) NOT NULL | למשל passenger/driver reminder |
| deliver_at | TIMESTAMPTZ NOT NULL | מתי לשלוח |
| sent_at | TIMESTAMPTZ | null = ממתין; אחרי שליחה מסומן |
| created_at | TIMESTAMPTZ NOT NULL | |

אינדקס חלקי: `idx_scheduled_notifications_deliver` על `deliver_at` WHERE `sent_at IS NULL`.

---

## Indexes

### מ-001_full_schema

| טבלה | שדות | שם Index | סיבה |
|------|------|----------|--------|
| conversations | user_id_1 | idx_conversations_user_1 | חיפוש שיחות לפי משתמש |
| conversations | user_id_2 | idx_conversations_user_2 | חיפוש שיחות לפי משתמש |
| messages | conversation_id | idx_messages_conversation | הודעות לפי שיחה |
| messages | conversation_id, created_at | idx_messages_created | מיון הודעות בזמן |
| messages | sender_id | idx_messages_sender_id | סינון הודעות לפי שולח (migration 012; ORM `__table_args__` עודכן) |
| chat_analysis | conversation_id | idx_chat_analysis_conversation | חיפוש ניתוח לפי שיחה |
| users | last_location | idx_users_location (GIST) | חיפוש מרחבי |
| rides | origin_geom | idx_rides_origin_geom (GIST) | חיפוש מרחבי |
| rides | destination_geom | idx_rides_destination_geom (GIST) | חיפוש מרחבי |
| outbox_events | created_at WHERE status='PENDING' | idx_outbox_events_pending | סריקת **`notification-worker`** / fallback polling למסלול Outbox (`run_outbox_worker`) |
| groups | invite_code | ix_groups_invite_code | join by invite |

### מ-004_add_missing_indexes

| טבלה | שדות | שם Index | סיבה |
|------|------|----------|--------|
| rides | driver_id, departure_time | idx_rides_driver_departure (DESC על `departure_time`) | רשימת נהג + מיון זמן יציאה; מחליף את `idx_rides_driver_id` (מיגרציה **018**) |
| rides | group_id, departure_time | idx_rides_group_departure (DESC; **WHERE group_id IS NOT NULL**) | נסיעות לפי קבוצה + מיון; מחליף את `idx_rides_group_id` (**018**) |
| rides | status | idx_rides_status | סינון לפי סטטוס |
| rides | departure_time, status | idx_ride_time_status | ORDER BY departure_time + WHERE status |
| bookings | ride_id | idx_bookings_ride | הזמנות לנסיעה |
| bookings | passenger_id | idx_bookings_passenger | הזמנות שלי |
| bookings | status | idx_bookings_status | סינון לפי סטטוס |
| group_members | group_id | idx_group_members_group_id | חברי קבוצה |
| group_members | user_id | idx_group_members_user_id | קבוצות של משתמש |
| passenger_requests | passenger_id | idx_passenger_requests_passenger_id | בקשות שלי |

---

## Migrations History

| Revision | תיאור | תאריך |
|----------|--------|--------|
| 001_full_schema | סכמה מלאה: enums, users, groups, group_members, rides, passenger_requests, bookings, conversations, messages, outbox_events, chat_analysis, indexes (001) | 2025-03-09 |
| 002_avatar_key (`002_rename_avatar_url_to_avatar_key.py`) | users.avatar_url → avatar_key | 2025-03-09 |
| 003_groups_avatar_desc | groups: avatar_key, description | 2025-03-09 |
| 004_add_missing_indexes | 11 indexes — rides (4), bookings (3), group_members (2), passenger_requests (1) | 2025-03-09 |
| 005_add_active_ride_status | הוספת ערך 'active' ל-enum ride_status (נסיעה בתנועה — התחל/סיים נסיעה, GPS) | 2025-03-09 |
| 006_chat_participants (`006_add_conversation_participants.py`) | טבלת `conversation_participants` (למשל `last_read_at` למשתמש בשיחה) | — |
| 007_last_active_at (קובץ `007_add_last_active_at.py`) | `users.last_active_at` — פעילות/צ'אט / last-seen | מזהה רוויזיה בקוד: `revision = "007_last_active_at"`; **008** מצביע אליו ב־`down_revision` |
| 008_scheduled_notifications | טבלת `scheduled_notifications` + partial index; הסרת `reminder_sent` מ-rides ו-bookings | — |
| 009_user_avatar_lifecycle (`009_user_avatar_lifecycle.py`) | מחזור חיים לאווטאר: `avatar_staging_key`, `avatar_status` | — |
| 010_outbox_notify_trigger (`010_outbox_notify_trigger.py`) | טריגר PostgreSQL LISTEN/NOTIFY על הכנסות ל־outbox | — |
| 011_chat_read_cursor (`011_chat_read_cursor.py`) | `last_read_message_id` ב־`conversation_participants` (קרסור קריאה) | — |
| 012_add_missing_indexes | אינדקסים משלימים: `bookings.request_id`, `messages.sender_id` | 2026-04-21 |
| 013_add_billing | טבלת `payments`, enum `payment_status_enum`, ושדות חיוב ב-`users` (`stripe_customer_id`, `is_premium`, `premium_since`) | 2026-04-23 |
| 014_fix_billing_partial_state | תיקון סכמת billing אחרי מצבים חלקיים (enum/עמודות/indexes idempotent) | 2026-04-23 |
| 015_add_audit_log | טבלת `audit_log` (אדמין + ניסיונות webhook billing) | 2026-04-26 |
| 015_billing_idem (`015_billing_idempotency_and_indexes.py`) | טבלת `idempotency_keys` + אינדקס חלקי `idx_payments_status_created` על `payments` | 2026-05-01 |
| 016_merge015_heads (`016_merge_015_audit_and_billing_heads.py`) | merge revision — מאחד את **`015_add_audit_log`** ו־**`015_billing_idem`** (אין שינוי סכמה) | 2026-05-01 |
| 017_set_statement_timeout (`017_set_statement_timeout.py`) | **Ceiling דיפנסיבי קשיח של 60000ms** ברמת role (`ALTER ROLE CURRENT_USER`) — literal, ללא תלות ב-`settings`; ערך אופרטיבי תחת ה-ceiling מוחל ברמת session דרך `connect_args.server_settings` ב-`app/db/session.py` (מ-`DB_STATEMENT_TIMEOUT_MS`, ברירת מחדל 30s). | 2026-05-06 |
| 018_rides_composite_indexes (`018_rides_composite_indexes.py`) | אינדקסים `idx_rides_driver_departure`, `idx_rides_group_departure` (חלקי); מחיקת `idx_rides_driver_id` / `idx_rides_group_id` כפולים | 2026-05-06 |
| 019_booking_lifecycle_enum (`019_booking_lifecycle_enum.py`) | הוספת **`en_route`**, **`arrived`**, **`trip_in_progress`** ל־enum **`booking_status`** — תואם ל־`BookingStatus` בקוד ול־`IN (...)` queries (סיכול bulk ביטול בקשה + צינור קריאות פעילות) | 2026-05-06 |
| 020_conversation_last_message_at (`020_add_conversations_last_message_at.py`) | הוספת `conversations.last_message_at`, backfill מ־`MAX(messages.created_at)` (fallback ל־`conversations.created_at`) ואינדקס `idx_conversations_last_message_at` | 2026-05-07 |

**הערת Alembic:** רוויזיות **`015_add_audit_log`** ו־**`015_billing_idem`** מתפצלות מ־**014**; המיזוג הוא **`016_merge015_heads`** בקובץ **`016_merge_015_audit_and_billing_heads.py`** (מזהי רוויזיה חייבים להתאים ל־`VARCHAR(32)` בטבלת **`alembic_version`** — לכן הסט מקוצר עבור מיגרציית האידמפוטנטיות).

**הרצה (מומלץ מקומית):** מתוך `backend/` עם **`uv`** — **`uv run alembic upgrade head`**; **`downgrade`** צעד אחד — **`uv run alembic downgrade -1`**. בשירות Docker **`migrate`**, התמונה בנויה עם **`ENTRYPOINT ["alembic"]`** — הפקודה היא **`alembic upgrade head`** (לא דרך `uv`). להקמת Postgres מקומית ומשתנה **`DATABASE_URL`**, ראו **`docs/architecture/DEVELOPMENT.md`**.

---

## Relationships (תרשים טקסטואלי)

```
users ◄──┬── rides (driver_id)
         ├── group_members (user_id)
         ├── bookings (passenger_id)
         ├── passenger_requests (passenger_id)
         ├── conversations (user_id_1, user_id_2)
         └── messages (sender_id)

groups ◄── rides (group_id), group_members (group_id)
rides  ◄── bookings (ride_id)
passenger_requests ◄── bookings (request_id)
conversations ◄── messages (conversation_id), chat_analysis (conversation_id)
```

---

## Race Condition Protection

פעולות שמוגנות עם **SELECT ... FOR UPDATE** (נעילה פסימית):

| פעולה | טבלה | מטרה |
|--------|------|--------|
| approve_booking | rides | נעילת נסיעה לפני עדכון מושבים וסטטוס — מונע double-approve ו-overbooking |
| cancel_booking | rides | נעילת נסיעה לפני החזרת סטטוס ל-OPEN ושחרור מושבים — מונע race עם approve |
| **Passenger cancel request** (`bulk_cancel_bookings_for_request`) | rides | לפני החזרת מושבים לבקשה (סטטוסים שתפסו מושב: confirmed / en_route / arrived / trip_in_progress) — `SELECT ride_id ... WITH FOR UPDATE` על כל הנסיעות המושפעות, ואז `UPDATE rides` פר־נסיעה |

מימוש: `get_ride_for_update(db, ride_id)` ב-`bookings/crud.py` משתמש ב־`AsyncSession` ומבצע `select(Ride).with_for_update()` כדי לנעול את שורת הנסיעה. ה-service קורא ל-crud זה לפני שינוי booking/ride. **`bulk_cancel_bookings_for_request`** נועל את שורות **`rides`** לפני עדכון `available_seats` כשמבטלים בקשת נוסע (`DELETE …/passengers/{id}/cancel`).

---

## Future / Recommendations (query performance)

No automated EXPLAIN ANALYZE pipeline exists. Manual review recommended on heavy paths (search, matching) using `pg_stat_statements` or Django-style query logging. דפוסי צמצום N+1 מתועדים ב-`ARCHITECTURE.md`:
- **My Bookings** / `BookingReadsService` — `joinedload` + aggregate per screen.
- **Chat inbox** / `get_inbox_aggregates` ([`backend/app/domain/chat/crud.py`](../../backend/app/domain/chat/crud.py)) — 3 `func.max` aggregate queries **למזהי השיחות בעמוד הנוכחי** (לא לכל האינבוקס), יחד עם `list_conversations_paginated`; מ-~3N ל-**4 קריאות קבועות לעמוד**. מיון העמוד עצמו עובר דרך `COALESCE(conversations.last_message_at, conversations.created_at)` (ללא correlated `MAX(...)` על כל שורה).
- **Bookings / groups read paths** — `get_user_bookings_with_relations` מוגבל ל-**100** שורות (פיד התראות נוסע); `cancel_ride_and_bookings` מרכז עדכון סטטוס `passenger_requests` אחרי ביטול; `get_member_counts_batch` לרשימת קבוצות — [`docs/FEATURE_DECISIONS.md#api-read-caps-batch-status`](../FEATURE_DECISIONS.md#api-read-caps-batch-status).

פירוט: `docs/ENGINEERING_HIGHLIGHTS.md`, [`docs/FEATURE_DECISIONS.md#chat-inbox-n1`](../FEATURE_DECISIONS.md#chat-inbox-n1), [`#chat-inbox-cursor-pagination`](../FEATURE_DECISIONS.md#chat-inbox-cursor-pagination).
