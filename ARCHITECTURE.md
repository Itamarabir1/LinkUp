# Architecture (Index Stub)

This root file intentionally stays short.

For the canonical architecture documentation, use:

- [`docs/DOCUMENTATION_MAP.md`](docs/DOCUMENTATION_MAP.md) — **where to look first** (onboarding / audit checklist)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system-wide architecture entry point
- [`docs/FUTURE_WORK.md`](docs/FUTURE_WORK.md) — deferred architecture decisions and rollout timing (כולל S.4 OCC ו-E.5/E.6 frontend forms scope)
- [`docs/FRONTEND_UPGRADE_ROADMAP.md`](docs/FRONTEND_UPGRADE_ROADMAP.md) — **מקור אמת** ל־backlog פרונט פתוח (RQ, Tier-1/2, אימותים)
- [`docs/operations/MONITORING.md`](docs/operations/MONITORING.md) — Sentry + Better Stack (קונסולות פרודקשן), Prometheus/Grafana, probes
- [`docs/FEATURE_DECISIONS.md`](docs/FEATURE_DECISIONS.md) — rationale/trade-offs, including Token Bucket + Sliding Window rate limiting
- [`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`](docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md) — frontend decisions including TanStack React Query (Stage 3a/3b), GroupContext/MyRides migration, auth forms with react-hook-form + zod, OpenAPI snapshot codegen (Orval), S.7 hybrid i18n/asset-hardening, Web Vitals D (Sentry RUM), and route-level a11y headings/landmarks policy (`main` + page-specific `h1` + `usePageTitle`)
- [`docs/architecture/DEVELOPMENT.md`](docs/architecture/DEVELOPMENT.md) — env/setup: Google Sign-In OAuth (`localhost:5173`), Firebase Model B (`FIREBASE_CREDENTIALS_JSON`), **`make test`** / **`uv run alembic`** מתוך `backend/`, Postgres ייעודי לטסטים ב־CI
- [`docs/FRONTEND_PERFORMANCE_RUNBOOK.md`](docs/FRONTEND_PERFORMANCE_RUNBOOK.md) — frontend performance operations (bundle budget checks, chunk audits, profiling workflow)
- [`docs/architecture/API.md`](docs/architecture/API.md)
- [`docs/architecture/DATABASE.md`](docs/architecture/DATABASE.md)
- [`docs/architecture/EVENTS.md`](docs/architecture/EVENTS.md)
- [`docs/architecture/REALTIME.md`](docs/architecture/REALTIME.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production deploy and runbook
- [`.github/dependabot.yml`](.github/dependabot.yml) — npm / pip / Docker (**per-directory** updates: **`/frontend`**, **`/backend`**, **`/infrastructure/pgbouncer`** — matches the file). Backend Python manifest: **`backend/pyproject.toml`** (+ **`backend/uv.lock`**); there is no backend `requirements.txt` at repo root.
- [`docs/SECURITY_HEADERS.md`](docs/SECURITY_HEADERS.md) — edge CSP (enforcing) + XSS layering with the web SPA (**`nginx/nginx.conf.template`** → `nginx/nginx.conf`, **`SENTRY_REPORT_URI`**, [`scripts/ops/render-nginx-conf.sh`](scripts/ops/render-nginx-conf.sh)); see also [`docs/FEATURE_DECISIONS.md`](docs/FEATURE_DECISIONS.md#browser-csp-edge)

Service-specific architecture docs:

- [`chat-ws/ARCHITECTURE.md`](chat-ws/ARCHITECTURE.md)
- [`frontend/docs/ARCHITECTURE.md`](frontend/docs/ARCHITECTURE.md)
