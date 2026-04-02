# Event System

Outbox → RabbitMQ → Worker. מקור אמת ל-routing: `backend/app/domain/events/routing.py`.

---

## Pattern: Outbox → RabbitMQ → Worker

1. **Backend** כותב אירוע ל-tבלת `outbox_events` (status=PENDING) באותה transaction עם שינוי עסקי.
2. **outbox-worker** קורא רשומות PENDING, מפרסם ל-RabbitMQ לפי `get_routing_metadata(event_name)`, מעדכן status ל-DONE (או retry).
3. **Consumers** ב-worker מקשיבים לתורים, מפעילים handlers (מייל, פוש, S3, וכו').

יתרון: at-least-once, אין איבוד אירועים אם RabbitMQ נופל.

---

## Exchanges

| Exchange | Type | Purpose |
|----------|------|---------|
| user | (default) | אירועי משתמש והתראות — רישום, אימות מייל, איפוס סיסמה, צ'אט |
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
| avatar_upload_queue | tasks | handle_avatar_upload_event | עיבוד S3 (resize), עדכון DB |
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

### Ride

| Event | Exchange | Routing Key | Triggered By | Payload |
|-------|----------|-------------|--------------|---------|
| ride.created_for_passengers | ride | ride.created_for_passengers | יצירת נסיעה (לנוסעים מתאימים) | ride_id, driver_id, ... |
| ride.cancelled_by_driver | ride | ride.cancelled_by_driver | ביטול נסיעה ע"י נהג | ride_id, ... |

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

## Workers (main_worker.py)

| Task | תיאור |
|------|--------|
| run_outbox_worker | Poll outbox_events (PENDING), publish ל-RabbitMQ לפי routing. |
| notifications_consumer.consume(handle_notification_event) | צורך notifications_queue, מפעיל handler — מייל/פוש לפי NotificationEvent. `handle_ride_cancelled_by_driver` טוען הזמנות ב-async SQL ושולח התראה רק ל-**PENDING** / **CONFIRMED** (לא לבוקינג שכבר **CANCELLED**). |
| avatar_upload_consumer.consume(handle_avatar_upload_event) | צורך avatar_upload_queue, עיבוד S3 ו-DB. |
| scheduled_tasks_consumer.consume(handle_scheduled_task) | צורך scheduled_tasks_queue, מפעיל reminders/fuel/maintenance/chat_timeout. |
| run_scheduled_tasks_publisher | מפרסם משימות מתוזמנות ל-scheduled exchange. |
| run_chat_completion_redis_listener | מאזין ל-Redis DB 1 (chat:completion:*), מפעיל ניתוח AI ושמירה. |

---

## Retry Policy

- **תורים עם retry:** notifications_queue, avatar_upload_queue.
- **מקסימום ניסיונות:** 3.
- **עיכובים (Exponential Backoff):** 5s → 30s → 5min.
- **אחרי 3 כישלונות:** ההודעה נשלחת ל-Dead Letter Queue (DLQ).

מימוש: `backend/app/infrastructure/rabbitmq/consumer.py` — `_handle_with_retry`, קבועים `RETRY_DELAYS_SEC`, `MAX_RETRIES`, `RETRYABLE_QUEUES`.

- **Outbox:** retry_count ו-last_error ב-outbox_events; ה-worker מפרסם ל-RabbitMQ לפי מדיניות.

---

## Dead Letter Queues

| Queue | Retry Queue | DLQ |
|-------|-------------|-----|
| notifications_queue | notifications_queue.retry | notifications_queue.dlq |
| avatar_upload_queue | avatar_upload_queue.retry | avatar_upload_queue.dlq |
| scheduled_tasks_queue | — | — |

תור ראשי עם `x-dead-letter-exchange` → dlq_exchange; הודעות שנכשלו אחרי כל הניסיונות עוברות ל-DLQ. תור retry עם TTL על ההודעה מחזיר אחרי פקיעה לתור הראשי.

---

## Scheduled Tasks

אין retry — המתזמן שולח הודעה חדשה במחזור הבא. כישלון ב-`handle_scheduled_task` נכתב ללוג (Scheduled task failed — will retry on next schedule) והודעה מקבלת ack.
