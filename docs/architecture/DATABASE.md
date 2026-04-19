# Database Architecture

PostgreSQL 15 + PostGIS. מקור: `backend/app/domain/*/model.py`, `backend/alembic/versions/`.

---

## Overview

- **Driver**: asyncpg (`postgresql+asyncpg://`).
- **Connection**: `backend/app/db/session.py` — `get_db()` מחזיר AsyncSession.
- **מדיה (קשר ל-S3, לא עמודה נפרדת):** שדות `avatar_key` ב-`users` / `groups` מחזיקים prefix או מפתח אובייקט ב-bucket; ה-API בונה URL ציבורי — עם **`CLOUDFRONT_DOMAIN`** (ראו `app/core/config.py`, `app/infrastructure/s3/service.py`) או presigned. פירוט תהליך אווטאר גרסתי: `ARCHITECTURE.md` (Features), `docs/ENGINEERING_HIGHLIGHTS.md` (סעיף 12).

---

## Connection Pool

מקור: `backend/app/db/session.py` — ערכים מ-`app.core.config.settings` (ניתן לעקוף ב-`.env`).

| Parameter | Env / default | הערות |
|-----------|----------------|--------|
| pool_size | `DB_POOL_SIZE` (default 5) | חיבורים קבועים במאגר |
| max_overflow | `DB_MAX_OVERFLOW` (default 10) | חיבורים נוספים מעבר ל-pool_size |
| pool_timeout | `DB_POOL_TIMEOUT` (default 30s) | המתנה לחיבור פנוי מהמאגר |
| pool_recycle | `DB_POOL_RECYCLE` (default 1800s) | מחזור חיבורים (למניעת חיבורים “מתים” אצל שרת ה-DB) |
| pool_pre_ping | True (קוד) | בודק חיבור לפני שימוש (מונע חיבורים מתים) |

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
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

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
| driver_id | UUID FK users NOT NULL | index (004) |
| group_id | UUID FK groups | index (004), nullable |
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
| status | booking_status ENUM NOT NULL | pending_approval, confirmed, rejected, cancelled, completed — index (004) |
| created_at, updated_at | TIMESTAMPTZ | |
| UNIQUE(ride_id, passenger_id) | | |

**קריאות מאוגדות (מסך “הזמנות שלי”):**

- **נהג:** `GET /bookings/driver-summary` — `select(Ride)` עם `joinedload` ל־`Ride.bookings` → `Booking.passenger_request` → `PassengerRequest.user`, ול־`Ride.group`; על ישות `Booking` בטעינה מוחלת **`with_loader_criteria`** כך שרק הזמנות בסטטוס **pending_approval** ו־**confirmed** נטענות לקולקציה (מימוש: [`get_driver_rides_with_passengers`](../../backend/app/domain/bookings/crud.py)).
- **נוסע:** `GET /bookings/passenger-summary` — `select(Booking)` עם `join` ל־`Ride`, `joinedload` ל־`ride.driver` ו־`ride.group`, מיון לפי `Ride.departure_time` ([`get_passenger_bookings_with_rides`](../../backend/app/domain/bookings/crud.py)).

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
| chat_analysis | conversation_id | idx_chat_analysis_conversation | חיפוש ניתוח לפי שיחה |
| users | last_location | idx_users_location (GIST) | חיפוש מרחבי |
| rides | origin_geom | idx_rides_origin_geom (GIST) | חיפוש מרחבי |
| rides | destination_geom | idx_rides_destination_geom (GIST) | חיפוש מרחבי |
| outbox_events | created_at WHERE status='PENDING' | idx_outbox_events_pending | poll של Outbox worker |
| groups | invite_code | ix_groups_invite_code | join by invite |

### מ-004_add_missing_indexes

| טבלה | שדות | שם Index | סיבה |
|------|------|----------|--------|
| rides | driver_id | idx_rides_driver_id | נסיעות שלי כנהג, WHERE driver_id |
| rides | group_id | idx_rides_group_id | נסיעות לפי קבוצה |
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
| 002_rename_avatar_url_to_avatar_key | users.avatar_url → avatar_key | 2025-03-09 |
| 003_groups_avatar_desc | groups: avatar_key, description | 2025-03-09 |
| 004_add_missing_indexes | 11 indexes — rides (4), bookings (3), group_members (2), passenger_requests (1) | 2025-03-09 |
| 005_add_active_ride_status | הוספת ערך 'active' ל-enum ride_status (נסיעה בתנועה — התחל/סיים נסיעה, GPS) | 2025-03-09 |
| 006_chat_participants | טבלת `conversation_participants` (למשל `last_read_at` למשתמש בשיחה) | — |
| 007_last_active_at (קובץ `007_add_last_active_at.py`) | `users.last_active_at` — פעילות/צ'אט / last-seen | מזהה רוויזיה בקוד: `revision = "007_last_active_at"`; **008** מצביע אליו ב־`down_revision` |
| 008_scheduled_notifications | טבלת `scheduled_notifications` + partial index; הסרת `reminder_sent` מ-rides ו-bookings | — |

הרצה: מתוך `backend/` — `alembic upgrade head`. downgrade: `alembic downgrade -1`.

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

מימוש: `get_ride_for_update(db, ride_id)` ב-`bookings/crud.py` משתמש ב־`AsyncSession` ומבצע `select(Ride).with_for_update()` כדי לנעול את שורת הנסיעה. ה-service קורא ל-crud זה לפני שינוי booking/ride.

---

## Future / Recommendations (query performance)

No automated EXPLAIN ANALYZE pipeline exists. Manual review recommended on heavy paths (search, matching) using `pg_stat_statements` or Django-style query logging. דפוסי צמצום N+1 מתועדים ב-`ARCHITECTURE.md` (My Bookings / `BookingReadsService`) וב-`docs/ENGINEERING_HIGHLIGHTS.md`.
