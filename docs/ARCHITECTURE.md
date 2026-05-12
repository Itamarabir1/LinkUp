# Architecture

This file is the canonical architecture entry point for Linkup.

![LinkUp — system overview](./assets/linkup-system-overview.png)

Also surfaced in the repo root [`README.md`](../README.md#architecture).

**מפת תיעוד לפי סוג משימה ומקורות אמת (Compose/CI/API):** [`docs/DOCUMENTATION_MAP.md`](DOCUMENTATION_MAP.md).

## High-level docs

- [`README.md`](../README.md) — product overview and getting started
- [`frontend/README.md`](../frontend/README.md) — web client architecture notes (RTL/i18n, realtime, Premium UX flow, React Query migrations כולל Stage 3b Part 2 ל-MyBookings (פעיל+היסטוריה, `useInfiniteQuery`+cursor), **MyRides** (`useInfiniteQuery`+cursor + `useMutation` + WS invalidation), Stage 3b Part 6 ל-SearchRides + **פרמטרי זמן ב־`GET search-rides`** (`buildManualRideSearchParams` / `searchMode`), Stage 5 cleanup ל-MyRequests/Auth bootstrap, Stage 3d safe-subset ל-Chat polling/fetch, **auth session teardown:** **`tearDownSession` + `auth:session-expired` + Sentry/RQ 401 policy** — **FEATURE_DECISIONS `#auth-session-teardown`** / **ADR Frontend §21**; **chat outbound:** `ChatListRow` optimistic UI + `applyInboundRealMessage` / `appendMessageDedupById` + ref-scoped Idempotency-Key — ADR Frontend §2; **chat reconnect gap:** dedicated **`/messages/gap?since_message_id=`** batches (separate from history keyset cursor); **history pagination:** opaque **`after`** cursor on `/messages`; **WS transport reconnect:** **`reconnectBackoff.ts`** (exponential + jitter) ב־`useChatWebSocket` / `useReconnectingWebSocket*`; **WS token freshness gate:** **`ensureFreshToken()`** ב-`tokenRefresh.ts` — פענוח `exp` client-side + coordinated refresh לפני כל reconnect + **`visibilitychange`** listener — **FEATURE_DECISIONS `#frontend-ws-token-freshness`**; **chat-ws inbound:** read cap + typing rate limit — ADR chat-ws §7, S.7 asset hardening, Web Vitals D: Sentry RUM + dynamic vitals metrics, Orval OpenAPI codegen + CI drift gate, A11y heading/landmarks cleanup עם `usePageTitle`; **XSS:** `react/no-danger` + **`sanitizeHtml()`** + backend chat plaintext (**`SECURITY_HEADERS`**, **`nginx/nginx.conf.template`** + **`SENTRY_REPORT_URI`**, **`scripts/ops/render-nginx-conf.sh`** ל-CSP ב-edge nginx)
- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) — production deployment on EC2 (centralized **`deploy-ec2.yml`**, CI tables, rollback)
- [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) — senior-level feature and reliability highlights
- [`docs/BILLING_REFACTOR_SUMMARY.md`](BILLING_REFACTOR_SUMMARY.md) — סיכום מלא של Billing refactor (לפני/אחרי, רכיבים, השוואת Kafka, טסטים)
- [`docs/SECURITY_HEADERS.md`](SECURITY_HEADERS.md) — **three-layer CSP:** edge nginx (enforcing SPA policy on 443 with HTTP/2, **`nginx/nginx.conf.template`** → **`nginx/nginx.conf`** via **`scripts/ops/render-nginx-conf.sh`** / CI `envsubst`), **backend middleware** (`SecurityHeadersMiddleware` — strict `default-src 'none'` on API JSON responses, relaxed for Swagger `/docs`/`/redoc`), frontend nginx (defense-in-depth non-CSP headers). TLS 1.2/1.3, SSL tuning in **`nginx/snippets/ssl-params.conf`** (ECDHE-only AEAD, OCSP stapling, HSTS with **`preload`**), **`SENTRY_REPORT_URI`** for CSP violation reporting, and XSS complement controls (plaintext chat, `sanitizeHtml`, static-SPA nonce limitations)
- [`docs/FUTURE_WORK.md`](FUTURE_WORK.md) — deferred decisions כולל S.4 OCC ל-Profile edit עתידי ו-E.5/E.6 forms scope rationale
- [`docs/FRONTEND_UPGRADE_ROADMAP.md`](FRONTEND_UPGRADE_ROADMAP.md) — פרונט: מה **כבר סגור** ב־checklist ומה **נשאר** (קבוצות manage, העלאות, CreateRide, MSW וכו׳)

## Architecture deep-dive by domain

- [`docs/architecture/API.md`](architecture/API.md) — FastAPI routes, auth, middleware, health contracts (**Billing:** checkout + **`X-Idempotency-Key`**, webhook, admin reconcile/stale-pending — סעיף Billing / Admin); זרימת preview גיאוגרף: קואורדינטות טקסט דרך **geocode cache**; **`GET …/passengers/me`** במודל **cursor pagination**; מניפסט נסיעה לנהג בתקרת שורות + טוטלים — ראו **FEATURE_DECISIONS** **`#geo-manifest-passenger-reads`**
- [`docs/architecture/DATABASE.md`](architecture/DATABASE.md) — PostgreSQL/PostGIS schema, indexes, migrations (incl. **021** — hashed refresh tokens, **022** — composite/partial indexes for hot CRUD queries, **023** — `notification_reads` server-side read-state, **025** — nullable `phone_number` + partial unique index for OAuth accounts), PgBouncer, Redis single-instance DB0/DB1 topology, and N+1 query elimination patterns (chat inbox aggregates, chat detail redundant re-fetch, pending bookings eager loading)
- [`docs/architecture/EVENTS.md`](architecture/EVENTS.md) — Outbox, RabbitMQ topology, retry/DLQ flow
- [`docs/architecture/REALTIME.md`](architecture/REALTIME.md) — WebSocket architecture, Redis pub/sub, GPS/presence
- [`docs/architecture/NOTIFICATIONS.md`](architecture/NOTIFICATIONS.md) — Outbox → workers, email (Brevo + **circuit breaker**), push (FCM + DB ניקוי טוקן על רישום לא תקף), in-app (**REST** + **`invalidate`/`UserEvent`** על **`user:{id}:events`**, מאזין ב־**`ChatContext`**); **`AsyncSession`** ב־`provider.send(..., db)`; **server-side read-state** (טבלת `notification_reads`, `PATCH /me/notifications/read{,-all}`, מחליף localStorage); **M3 error classification:** `TransientNotificationError` / `PermanentNotificationError` hierarchy with Redis dedup guard (24h TTL)
- [`docs/architecture/AI.md`](architecture/AI.md) — AI chat-summary pipeline (**`ai-worker`**, Groq, Redis completion)
- [`docs/architecture/STORAGE.md`](architecture/STORAGE.md) — S3 presigned uploads, avatar versioning, CloudFront קריאה, מחיקת prefix ב-DeleteObjects batches והסרת אווטאר דרך outbox + worker
- [`docs/architecture/DEVELOPMENT.md`](architecture/DEVELOPMENT.md) — local/dev architecture and setup conventions

## Container healthchecks

All long-running services define Docker healthchecks: **backend** (`GET /readyz` via Python urllib), **chat-ws** (`wget /healthz`), **workers** (`notification-worker`, `task-worker`, `ai-worker`) use PID-based liveness (`python -c "import os; os.kill(1, 0)"` — signal-0 to PID 1 detects main process crash), **db** (`pg_isready`), **pgbouncer** (`psql SELECT 1`), **redis** (`redis-cli ping`), **rabbitmq** (`rabbitmq-diagnostics ping`), **email-renderer** (HTTP `/health`), **frontend** (`wget /config.js`).

## Container resource limits

All services in `docker-compose.yml` are constrained via **YAML extension-field profiles** (`x-resources-micro`, `x-resources-light`, `x-resources-medium`, `x-resources-redis`) defined at the top of the file. Each service merges one profile (`<<: *resources-<tier>`), providing a single source of truth for memory limits, reservations, swap protection, CPU caps, and PID limits. Budget is sized for a **t3.medium** (4096MB; ~3500MB usable after OS+Docker). Steady-state total: **3264MB**. Monitoring profile (`prometheus` + `grafana`) adds 768MB and requires a t3.large or temporary activation only.

## Container log rotation

All 16 services reference `logging: *default-logging` from the shared `x-default-logging` extension field (`json-file` driver, `max-size: 10m`, `max-file: 3`). Caps each container at 30MB of retained log files — prevents disk exhaustion on long-running EC2 instances without losing recent debug context.

## Monitoring network exposure

Prometheus and Grafana ports are bound to `127.0.0.1` in `docker-compose.yml` (not `0.0.0.0`). Access from a workstation requires an SSH tunnel (`ssh -L 9090:127.0.0.1:9090 ec2-host`).

## Supply chain & automation

- **CI supply chain hardening:** כל GitHub Actions ב-6 workflow files מקובעים ל-**commit SHA** (`uses: owner/action@<sha> # vX`) ולא ל-mutable tags — מונע הרצת קוד זדוני אם tag מוזז. Dependabot `github-actions` ecosystem מציע עדכוני SHA ב-PR אוטומטי.
- [`.github/dependabot.yml`](../.github/dependabot.yml) — scheduled PRs: npm (`/frontend`), pip על **`/backend`** (מעקב אחר **`backend/pyproject.toml`** + **`backend/uv.lock`**; אין `requirements.txt` ב-backend), Docker (`/backend`, `/frontend`, `/infrastructure/pgbouncer`), **github-actions** (`/`, weekly)
- **CI/CD:** [`backend-ci.yml`](../.github/workflows/backend-ci.yml), [`frontend-ci.yml`](../.github/workflows/frontend-ci.yml), [`chat-ws-ci.yml`](../.github/workflows/chat-ws-ci.yml), [`email-renderer-ci.yml`](../.github/workflows/email-renderer-ci.yml) (בנייה ו־push ל־GHCR לפי path filters); [`openapi-contract.yml`](../.github/workflows/openapi-contract.yml) (backend↔frontend OpenAPI schema drift detection); פריסת EC2 מרוכזת ב־[`deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml) (`workflow_run` אחרי CI מוצלח על `main`) — טבלה ופירוט ב־[`docs/DEPLOYMENT.md`](DEPLOYMENT.md)

## Operations docs

- [`docs/operations/RUNBOOK.md`](operations/RUNBOOK.md) — incident handling for common production failures
- [`docs/operations/MONITORING.md`](operations/MONITORING.md) — dashboards חיצוניים בפרודקשן (**Sentry**, **Better Stack**), Prometheus/Grafana, SLO baseline, probe exposure policy (`/livez` public ל-synthetics, `/readyz` internal-only ב-nginx; ב־**`docker-compose.yml`** ה־**`backend`** healthcheck פוגע ב־`/readyz` ישירות בתוך הקונטיינר), ומטריקות **billing** (`billing_reconciler_*`, …)
- [`docs/BACKUP_AND_RECOVERY.md`](BACKUP_AND_RECOVERY.md) — automated PostgreSQL backup pipeline (daily pg_dump → AES-256 encrypt → S3), pre-deploy backups, restore procedures, disaster recovery runbook

## ADRs

- [`docs/adr/README.md`](adr/README.md)
- [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md)
- [`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`](adr/ARCHITECTURE_DECISIONS_FRONTEND.md)
- [`docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md`](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md) — §1–§8 (כולל §8: הקשחה תפעולית H7–H11 — `/healthz` + subscriber liveness, graceful shutdown, pong/read deadline, panic recovery, `sync.Once`-guarded `Conn.Close()`)
