# Event System

Outbox → RabbitMQ → Worker. מקור אמת ל-routing: `backend/app/domain/events/routing.py`.

---

## Pattern: Outbox → RabbitMQ → Worker

1. **Backend** כותב אירוע ל-tבלת `outbox_events` (status=PENDING) באותה transaction עם שינוי עסקי.
2. **notification-worker** מריץ `run_outbox_worker`, קורא רשומות PENDING ומפרסם ל-RabbitMQ לפי `get_routing_metadata(event_name)`, ואז מעדכן status ל-DONE (או retry). ה-fetch של **PENDING** משתמש ב-**`SELECT ... FOR UPDATE SKIP LOCKED`** ([`OutboxRepository.get_pending_events`](../../backend/app/infrastructure/outbox/repository.py)) — כך **כמה מופעי worker** יכולים לרוץ במקביל בלי נעילה הדדית על אותה שורה (מדלגים לשורה הבאה הזמינה).
3. **Consumers** רצים ב-workers הייעודיים (notification/task) ומפעילים handlers (מייל, פוש, S3, וכו').

יתרון: at-least-once, אין איבוד אירועים אם RabbitMQ נופל.

---

## Exchanges

| Exchange | Type | Purpose |
|----------|------|---------|
| user | (default) | אירועי משתמש והתראות — רישום, אימות מייל, איפוס סיסמה, צ'אט, billing |
| ride | — | אירועי נסיעה — יצירה, ביטול |
| booking | — | אירועי הזמנות — בקשת הצטרפות, אישור, דחייה |
| tasks | — | משימות כבדות — העלאת/הסרת אווטאר (S3) |
| system_events | DEFAULT_EXCHANGE | ברירת מחדל |
| scheduled | — | משימות מתוזמנות — תזכורות, fuel scan, maintenance, chat_timeout |

---

## Queues

| Queue | Exchanges | Consumer | Purpose |
|-------|-----------|----------|---------|
| notifications_queue | user, ride, booking, system_events | handle_notification_event | שליחת מייל (Brevo), פוש (Firebase) |
| avatar_upload_queue | tasks | handle_avatar_upload_event | עיבוד S3 (resize), העלאה ל־`avatars/{user_id}/v{version}/`, commit ל-`avatar_key`, מחיקת גרסה קודמת (best-effort) אחרי commit |
| scheduled_tasks_queue | scheduled | handle_scheduled_task | תזכורות, fuel scan, maintenance, chat timeout |

---

## Events (Outbox → RabbitMQ)

### Auth & User

| Event | Exchange | Routing Key | Triggered By | Payload (עיקרי) |
|-------|----------|-------------|--------------|------------------|
| auth.email_verification | user | auth.email_verification | רישום / אימות מייל | email, user_id, code/link |
| auth.password_reset_code | user | auth.password_reset_code | בקשת איפוס סיסמה | email, user_id, code |
| user.registered | user | user.registered | רישום מוצלח | user_id, email, ... |
| user.avatar_upload | tasks | user.avatar_upload | confirm_avatar_upload | user_id, staging_key |
| user.avatar_remove | tasks | user.avatar_remove | remove_avatar | user_id |

### Billing

| Event | Exchange | Routing Key | Triggered By | Payload |
|-------|----------|-------------|--------------|---------|
| billing.* | user | billing.<name> | Billing service / future billing outbox events | payment_id, user_id, status, provider ids |

### Ride

| Event | Exchange | Routing Key | Triggered By | Payload |
|-------|----------|-------------|--------------|---------|
| **ride.created** | ride | **ride.created** | `RideService._persist_ride_and_publish_event` אחרי `INSERT` לנסיעה | `{ "ride_id": "<uuid>" }` בלבד — מופיע ב-Outbox וב-RabbitMQ |
| ride.cancelled_by_driver | ride | ride.cancelled_by_driver | ביטול נסיעה ע"י נהג | ride_id, ... |

**חשוב — לא לבלבל עם שם האירוע הפנימי למייל:** ההתראה לנוסעים משתמשת במחרוזת האירוע **`ride.created_for_passengers`** רק בתוך `notification_handler.handle_event` (כלומר בשכבת התבניות/Brevo), וזה **לא** routing key שנפרסם מחדש ל-RabbitMQ. אחרי שהצרכן מקבל `ride.created`, הקוד ב-[`notification_tasks.handle_ride_created`](../../backend/app/workers/tasks/notification_tasks.py) טוען את הנסיעה, קורא ל-[`find_passengers_for_ride_notification`](../../backend/app/domain/passengers/crud.py), ולכל `PassengerRequest` מתאים קורא ל-handler עם `event_name=ride.created_for_passengers` ו-`payload` שכולל `ride_id` + `passenger_id`.

#### זרימה מתומצתת (התראת נוסע על נסיעה חדשה)

1. פרסום נסיעה → commit + שורת Outbox **`ride.created`**.
2. `notification-worker` → Outbox dispatcher מפרסם ל-exchange **`ride`** עם **`routing_key=ride.created`**.
3. אותו תהליך Worker → consumer על **`notifications_queue`** מקבל `routing_key=ride.created` ומפעיל **`handle_ride_created`**.
4. **אין יצירת Booking אוטומטית** — רק התראת מייל (וכל ערוץ נוסף שיוגדר בעתיד) לפי ההתאמה הגיאוגרפית.

פירוט סינון (רדיוסים, חלון תאריכים, `group_id`): ראו גם `docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §17 ו-[`ARCHITECTURE.md`](../../ARCHITECTURE.md) (פסקת נוסע).

### Booking

| Event | Exchange | Routing Key | Triggered By | Payload |
|-------|----------|-------------|--------------|---------|
| booking.passenger_join_request | booking | booking.passenger_join_request | request_to_join | booking_id, ride_id, passenger_id, ... |
| booking.approved_by_driver | booking | booking.approved_by_driver | approve_booking | booking_id, ... |
| booking.rejected_by_driver | booking | booking.rejected_by_driver | reject_booking | booking_id, ... |

### Chat

| Event | Exchange | Routing Key | Triggered By | Payload |
|-------|----------|-------------|--------------|---------|
| chat.conversation.completed | user | chat.conversation.completed | סיום שיחה (מ-chat-ws/backend → Redis → worker) | conversation_id, trigger_user_id |

### Scheduled (נשלח ע"י Scheduler ל-RabbitMQ, לא מ-Outbox)

| Routing Key | Queue | Purpose |
|-------------|--------|---------|
| reminders | scheduled_tasks_queue | תזכורות: ה-worker מפעיל `ReminderScheduler` שקורא שורות **due** מטבלת `scheduled_notifications` (לא סריקת rides/bookings לפי `reminder_sent`) |
| fuel_scan | scheduled_tasks_queue | סריקת מחירי דלק (EIA) |
| maintenance | scheduled_tasks_queue | משימות תחזוקה |
| chat_timeout | scheduled_tasks_queue | timeout שיחות |

---

## Workers (split entrypoints)

| Worker | Tasks | תיאור |
|--------|-------|--------|
| notification-worker | `run_outbox_worker`, `notifications_consumer.consume(handle_notification_event)`, `run_dlq_monitor` | עיבוד outbox והתראות (מייל/פוש/refresh UI) + ניטור עומק DLQ. |
| task-worker | `avatar_upload_consumer.consume(handle_avatar_upload_event)`, `scheduled_tasks_consumer.consume(handle_scheduled_task)`, `run_scheduled_tasks_publisher` | משימות כבדות + scheduler. |
| ai-worker | `run_chat_completion_redis_listener` | מאזין ל־`chat:completion:*` על Redis חיבור הצ’אט; **לא** טריגיר העיקרי היום — ראו **`task-worker`** + [`AI.md`](AI.md). |

---

## RabbitMQ Connection Topology

- `rabbit_client` (API publish path): חיבור ייעודי לפרסומים מה-API.
- `outbox_rabbit_client` (Outbox publish path): חיבור ייעודי לפרסום `notification-worker` מתוך ה-Outbox.
- `worker_rabbit_client` (Worker consume/publish path): חיבור משותף ל-consumers ול-scheduled publisher, עם channels מבודדים לכל consumer.
- הגדרת queue behavior מרוכזת ב-`backend/app/infrastructure/rabbitmq/topology.py` דרך `QueueSpec`.

---

## Retry Policy

- **תורים עם retry:** notifications_queue, avatar_upload_queue.
- **מקסימום ניסיונות:** 3.
- **עיכוב retry:** broker-native TTL queue (ברירת מחדל 30s).
- **אחרי 3 כישלונות:** ההודעה מועברת ל-Dead Letter Queue (DLQ).

מימוש: `backend/app/infrastructure/rabbitmq/consumer.py` — `_handle_with_retry`; retry path מתבסס על `nack(requeue=False)` ל-`retry_exchange` + `x-message-ttl` על `<queue>.retry`, וספירה לפי `x-death` של התור הראשי. קביעת retryability/delay/retry-cap דרך `QueueSpec` ב-`backend/app/infrastructure/rabbitmq/topology.py`.

- **Outbox:** retry_count ו-last_error ב-outbox_events; ה-worker מפרסם ל-RabbitMQ לפי מדיניות.

---

## Dead Letter Queues

| Queue | Retry Queue | DLQ |
|-------|-------------|-----|
| notifications_queue | notifications_queue.retry | notifications_queue.dlq |
| avatar_upload_queue | avatar_upload_queue.retry | avatar_upload_queue.dlq |
| scheduled_tasks_queue | — | — |

תור ראשי עם `x-dead-letter-exchange` → `retry_exchange`; תור `<queue>.retry` עם `x-message-ttl` מחזיר אחרי פקיעה לתור הראשי; אחרי מיצוי נסיונות ההודעה נשלחת ל-`<queue>.dlq`.

**מדיניות איבוד:** Messages that fail after `max_retries=3` (מוגדר ב-`QueueSpec`) נשלחות ל-`.dlq` הייעודי — **לא אובדות**. `scheduled_tasks_queue` נשאר **ללא DLQ** by design (failures are logged and acked; the scheduler emits again on next cycle).

---

## DLQ Monitoring

- `notification-worker` מריץ `run_dlq_monitor` (כל 60s) ובודק עומק תורי DLQ של תורים retry-enabled.
- thresholds מובנים:
  - warning: `>=10`
  - critical: `>=50`
- אין side effects על messages; זה ניטור לוגי בלבד לצורך תפעול/התראות.

---

## DLQ Replay Tooling

- כלי תפעולי: `scripts/ops/rabbitmq-dlq-replay.py`
- replay מבוקר מתורי DLQ לתורים הראשיים (`<queue>.dlq` -> `<queue>`), עם:
  - בחירת תור (`--queue`)
  - הגבלת כמות (`--limit`)
  - מצב תצוגה בלבד (`--dry-run`)
- הפלט הוא דוח JSON תפעולי עם כמות replay/שגיאות/יתרה.

---

## Scheduled Tasks

אין retry — המתזמן שולח הודעה חדשה במחזור הבא. כישלון ב-`handle_scheduled_task` נכתב ללוג (Scheduled task failed — will retry on next schedule) והודעה מקבלת ack.
