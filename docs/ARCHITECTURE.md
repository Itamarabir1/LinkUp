# Architecture

This file is the canonical architecture entry point for Linkup.

![LinkUp — system overview](./assets/linkup-system-overview.png)

Also surfaced in the repo root [`README.md`](../README.md#architecture).

## High-level docs

- [`README.md`](../README.md) — product overview and getting started
- [`frontend/README.md`](../frontend/README.md) — web client architecture notes (RTL/i18n, realtime, Premium UX flow, React Query migrations כולל Stage 3b Part 2 ל-MyBookings, Stage 3b Part 6 ל-SearchRides, Stage 5 cleanup ל-MyRequests/Auth bootstrap, Stage 3d safe-subset ל-Chat polling/fetch, **chat outbound: `ChatListRow` optimistic UI + `applyInboundRealMessage` / `appendMessageDedupById` + ref-scoped Idempotency-Key** — ADR Frontend §2; **chat reconnect gap:** **`fetchMissedGap`** (`after` + `before=cursor`, capped multi-page REST) על `WS onOpen`; **chat-ws inbound:** read cap + typing rate limit — ADR chat-ws §7, S.7 asset hardening, Web Vitals D: Sentry RUM + dynamic vitals metrics, Orval OpenAPI codegen + CI drift gate, A11y heading/landmarks cleanup עם `usePageTitle`, ו-XSS baseline: `react/no-danger` + centralized `sanitizeHtml`)
- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) — production deployment flow and rollback
- [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) — senior-level feature and reliability highlights
- [`docs/SECURITY_HEADERS.md`](SECURITY_HEADERS.md) — nginx edge hardening policy (`HTTP/2`, browser security headers, CSP rollout)
- [`docs/FUTURE_WORK.md`](FUTURE_WORK.md) — deferred decisions כולל S.4 OCC ל-Profile edit עתידי ו-E.5/E.6 forms scope rationale

## Architecture deep-dive by domain

- [`docs/architecture/API.md`](architecture/API.md) — FastAPI routes, auth, middleware, health contracts
- [`docs/architecture/DATABASE.md`](architecture/DATABASE.md) — PostgreSQL/PostGIS schema, indexes, and migrations
- [`docs/architecture/EVENTS.md`](architecture/EVENTS.md) — Outbox, RabbitMQ topology, retry/DLQ flow
- [`docs/architecture/REALTIME.md`](architecture/REALTIME.md) — WebSocket architecture, Redis pub/sub, GPS/presence
- [`docs/architecture/NOTIFICATIONS.md`](architecture/NOTIFICATIONS.md) — Outbox → workers, email (Brevo + **circuit breaker**), push (FCM), in-app WS
- [`docs/architecture/AI.md`](architecture/AI.md) — AI subsystem architecture (placeholder, to be expanded)
- [`docs/architecture/STORAGE.md`](architecture/STORAGE.md) — media/storage architecture (placeholder, to be expanded)
- [`docs/architecture/DEVELOPMENT.md`](architecture/DEVELOPMENT.md) — local/dev architecture and setup conventions

## Operations docs

- [`docs/operations/RUNBOOK.md`](operations/RUNBOOK.md) — incident handling for common production failures
- [`docs/operations/MONITORING.md`](operations/MONITORING.md) — Prometheus/Grafana, SLO baseline, and probe exposure policy (`/livez` public, `/readyz` internal-only)

## ADRs

- [`docs/adr/README.md`](adr/README.md)
- [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md)
- [`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`](adr/ARCHITECTURE_DECISIONS_FRONTEND.md)
- [`docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md`](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md)
