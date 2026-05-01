# Notifications architecture

Canonical overview of how outbound notifications are produced, rendered, and delivered.

## Pipeline (high level)

1. **Domain / Outbox** — business code writes `outbox_events` in the same DB transaction as the state change; `outbox-worker` publishes to RabbitMQ (see [`EVENTS.md`](EVENTS.md)).
2. **`notification-worker`** — consumes `notifications_queue`, runs `notification_tasks` handlers (async SQLAlchemy), resolves templates and channels.
3. **Channels**
   - **Email:** HTML from **`email-renderer`** (`POST /render` with React Email templates), then SMTP send via **Brevo** transactional API (`sib_api_v3_sdk`).
   - **Push:** FCM with **data-only** payloads (see [`../FCM_SYSTEM_SUMMARY.md`](../FCM_SYSTEM_SUMMARY.md), [`../adr/FCM_AND_PUSH.md`](../adr/FCM_AND_PUSH.md)).
   - **In-app:** WebSocket feed on **`GET /api/v1/notifications/ws`** (FastAPI) — separate from chat-ws; see [`REALTIME.md`](REALTIME.md).

## Email — Brevo + circuit breaker

- **Implementation:** [`backend/app/domain/notifications/channels/email/client.py`](../../backend/app/domain/notifications/channels/email/client.py) — `EmailClient.send` checks **`brevo_email_cb.allow_request()`** before any SDK call. The retried Brevo call lives on **`_send_with_retry`** (Tenacity: up to 3 attempts with exponential backoff for `ApiException` / `ConnectionError`). On success → **`record_success()`** once; after all retries fail on those types → **`record_failure()`** once per logical `send()`. Missing **`BREVO_API_KEY`** raises **`ValueError`** before the circuit breaker (misconfiguration, not counted as provider failure).
- **Singleton:** [`backend/app/infrastructure/notifications/circuit_breaker.py`](../../backend/app/infrastructure/notifications/circuit_breaker.py) — **`brevo_email_cb`** (defaults aligned with geo: threshold **5**, recovery **60s**).
- **Shared class:** [`backend/app/infrastructure/circuit_breaker.py`](../../backend/app/infrastructure/circuit_breaker.py) — generic **`CircuitBreaker`** with injected Prometheus gauge (same semantics as Google Maps breakers).
- **Metrics:** `brevo_circuit_breaker_state{name="brevo_email"}` — **0** = closed, **1** = half_open, **2** = open (see [`../operations/MONITORING.md`](../operations/MONITORING.md)).
- **Failure when open:** [`EmailProviderCircuitOpenError`](../../backend/app/core/exceptions/infrastructure.py) — HTTP **503**, `error_code` **`EMAIL_CIRCUIT_OPEN`** (workers should treat as transient / retry via RabbitMQ policy).
- **Health (informational):** [`GET /api/v1/health`](API.md#health) includes **`circuit_breakers.brevo_email`**; it does **not** affect overall **`status`** (readiness is still DB + Redis + RabbitMQ only).

## Retry / DLQ / replay

- Broker-native retry via `retry_exchange` + per-queue `.retry` TTL queues; terminal failures → per-queue DLQ. Operational replay: `scripts/ops/rabbitmq-dlq-replay.py` — see [`EVENTS.md`](EVENTS.md).

## Further reading

- [`EVENTS.md`](EVENTS.md) — routing keys, outbox, queues
- [`../DEPLOYMENT.md`](../DEPLOYMENT.md) — compose / env
- [`../adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) §20 — circuit breaker ADR (Maps + Brevo)
