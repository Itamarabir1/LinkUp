# Notifications architecture

Canonical overview of how outbound notifications are produced, rendered, and delivered.

## Pipeline (high level)

1. **Domain / Outbox** — business code writes `outbox_events` in the same DB transaction as the state change (see [`EVENTS.md`](EVENTS.md)).
2. **`notification-worker`** (`python -m app.workers.notification_worker`) — dispatches **Outbox → RabbitMQ** (וערכי `REDIS` דרך `RedisChatPublisher` כשמוגדרים ב-`targets`), then consumes **`notifications_queue`**, runs `notification_tasks` handlers (async SQLAlchemy), resolves templates and channels.
   - **Outbox wake path:** `run_outbox_worker` uses **`OutboxListener`** with **`DATABASE_URL_DIRECT`** (direct Postgres; env `POSTGRES_HOST_DIRECT` / `POSTGRES_PORT_DIRECT`, defaults `db` / `5432`) because **PgBouncer transaction pooling does not deliver `NOTIFY` to clients** — using the pooled DSN would silently fall back to ~30s polling. Application SQLAlchemy sessions still use the normal `DATABASE_URL` through PgBouncer.
3. **Channels**
   - **Email:** HTML from **`email-renderer`** (`POST /render` with React Email templates), then SMTP send via **Brevo** transactional API (`sib_api_v3_sdk`).
   - **Push:** FCM with **data-only** payloads (see [`../FCM_SYSTEM_SUMMARY.md`](../FCM_SYSTEM_SUMMARY.md), [`../adr/FCM_AND_PUSH.md`](../adr/FCM_AND_PUSH.md)).
   - **In-app (רשימה):** **`GET /api/v1/users/me/notifications`** — מקור אמת עם **cursor pagination** (`limit`, `after` → `items`, `next_cursor`, `has_more`, `limit`), keyset order `created_at DESC, booking_id DESC`. במסך התראות: `useInfiniteQuery` עם `qk.notifications.page(20)`; בבאדג'ים: `useChatNotificationsFeed` מושך עמוד ראשון (`limit=20`) כל ~5 דקות. **רענון חי:** [`WebSocketProvider`](../../backend/app/domain/notifications/providers/websocket_provider.py) מפרסם ל־**`user:{user_id}:events`** פריים **`invalidate`** עם **`resource: "notifications"`** (+ `event` / `user_id`). בפרונט: **`ChatContext.handleInvalidate`** — `refreshUnreadNotifications`, **`NOTIFICATIONS_REFRESH_EVENT`**, ובתנאי — **`linkup:user-event`** — ראו [`REALTIME.md`](REALTIME.md). המאזין: [`ChatContext.tsx`](../../frontend/src/context/ChatContext.tsx) + [`useUserEventStream`](../../frontend/src/hooks/useUserEventStream.ts). אין כרגע WS נפרד **`/api/v1/notifications/ws`** ב-FastAPI.

## Providers and DB session

- [`BaseNotificationProvider`](../../backend/app/domain/notifications/providers/base.py) defines **`send(user, template_name, context, db=None)`** where **`db`** is an optional SQLAlchemy **`AsyncSession`**.
- [`NotificationCommand`](../../backend/app/domain/notifications/manager.py) carries **`db`** from [`NotificationHandler._dispatch`](../../backend/app/domain/notifications/core/handler.py) (same session as the worker/handler transaction). [`notification_manager`](../../backend/app/domain/notifications/manager.py) passes **`db=cmd.db`** into every provider **`send`**.
- **Email** ignores **`db`**. **[`WebSocketProvider`](../../backend/app/domain/notifications/providers/websocket_provider.py)** מקבל **`db`** בחתימה (**תאימות ל־`BaseNotificationProvider.send`**) אך **אינו משתמש** ב-session לפרסום Redis. **Push** uses **`db`** when Firebase returns **`UnregisteredError`** or **`SenderIdMismatchError`**: [`PushProvider`](../../backend/app/domain/notifications/providers/push_provider.py) calls **`crud_user.update_fcm_token(..., token=None)`** to clear **`users.fcm_token`** before re-raising, so stale device registrations do not accumulate server-side.

## Email — Brevo + circuit breaker

- **Implementation:** [`backend/app/domain/notifications/channels/email/client.py`](../../backend/app/domain/notifications/channels/email/client.py) — `EmailClient.send` checks **`brevo_email_cb.allow_request()`** before any SDK call. The retried Brevo call lives on **`_send_with_retry`** (Tenacity: up to 3 attempts with exponential backoff for `ApiException` / `ConnectionError`). On success → **`record_success()`** once; after all retries fail on those types → **`record_failure()`** once per logical `send()`. Missing **`BREVO_API_KEY`** raises **`ValueError`** before the circuit breaker (misconfiguration, not counted as provider failure).
- **Singleton:** [`backend/app/infrastructure/notifications/circuit_breaker.py`](../../backend/app/infrastructure/notifications/circuit_breaker.py) — **`brevo_email_cb`** (defaults aligned with geo: threshold **5**, recovery **60s**).
- **Shared class:** [`backend/app/infrastructure/circuit_breaker.py`](../../backend/app/infrastructure/circuit_breaker.py) — generic **`CircuitBreaker`** with injected Prometheus gauge (same semantics as Google Maps breakers).
- **Metrics:** `brevo_circuit_breaker_state{name="brevo_email"}` — **0** = closed, **1** = half_open, **2** = open (see [`../operations/MONITORING.md`](../operations/MONITORING.md)).
- **Failure when open:** [`EmailProviderCircuitOpenError`](../../backend/app/core/exceptions/infrastructure.py) — HTTP **503**, `error_code` **`EMAIL_CIRCUIT_OPEN`** (workers should treat as transient / retry via RabbitMQ policy).
- **Health (informational):** [`GET /api/v1/health`](API.md#health) includes **`circuit_breakers.brevo_email`**; it does **not** affect overall **`status`** (readiness is still DB + Redis + RabbitMQ only).

## Event → channel mapping (notable entries)

Full mapping: [`backend/app/domain/notifications/config/mappings.py`](../../backend/app/domain/notifications/config/mappings.py). Notable additions:

- **`BOOKING_CANCELLED_BY_PASSENGER`** — role: **driver**, template: `passenger_cancelled`, channels: **[email, push, websocket]**. Fires only when a **passenger** cancels a **confirmed** booking (not pending). Outbox written in `cancel_booking()` before `db.commit()`.
- **`PICKUP_REMINDER_PASSENGER`** / **`RIDE_START_DRIVER`** — channels: **[email, push]** (push added alongside email). Push templates `reminder_passenger` / `reminder_driver` in [`push_conf.py`](../../backend/app/domain/notifications/config/templates_map/push_conf.py).

## Retry / DLQ / replay

- Broker-native retry via `retry_exchange` + per-queue `.retry` TTL queues; terminal failures → per-queue DLQ. Operational replay: `scripts/ops/rabbitmq-dlq-replay.py` — see [`EVENTS.md`](EVENTS.md).

## Further reading

- [`EVENTS.md`](EVENTS.md) — routing keys, outbox, queues
- [`../DEPLOYMENT.md`](../DEPLOYMENT.md) — compose / env
- [`../adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) §20 — circuit breaker ADR (Maps + Brevo)
