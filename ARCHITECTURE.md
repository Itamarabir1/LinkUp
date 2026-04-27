# Architecture (Index Stub)

This root file intentionally stays short.

For the canonical architecture documentation, use:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system-wide architecture entry point
- [`docs/FUTURE_WORK.md`](docs/FUTURE_WORK.md) — deferred architecture decisions and rollout timing (כולל S.4 OCC ו-E.5/E.6 frontend forms scope)
- [`docs/FEATURE_DECISIONS.md`](docs/FEATURE_DECISIONS.md) — rationale/trade-offs, including Token Bucket + Sliding Window rate limiting
- [`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`](docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md) — frontend decisions including TanStack React Query (Stage 3a/3b), GroupContext/MyRides migration, auth forms with react-hook-form + zod, OpenAPI snapshot codegen (Orval), S.7 hybrid i18n/asset-hardening, Web Vitals D (Sentry RUM), and route-level a11y headings/landmarks policy (`main` + page-specific `h1` + `usePageTitle`)
- [`docs/architecture/DEVELOPMENT.md`](docs/architecture/DEVELOPMENT.md) — env/setup runbook including Google Sign-In local OAuth origin/redirect requirements (`localhost:5173`) and per-environment client-id strategy
- [`docs/architecture/DEVELOPMENT.md`](docs/architecture/DEVELOPMENT.md) — env/setup runbook including production Model B Firebase secret contract (`FIREBASE_CREDENTIALS_JSON`) and deploy validation workflow
- [`docs/FRONTEND_PERFORMANCE_RUNBOOK.md`](docs/FRONTEND_PERFORMANCE_RUNBOOK.md) — frontend performance operations (bundle budget checks, chunk audits, profiling workflow)
- [`docs/architecture/API.md`](docs/architecture/API.md)
- [`docs/architecture/DATABASE.md`](docs/architecture/DATABASE.md)
- [`docs/architecture/EVENTS.md`](docs/architecture/EVENTS.md)
- [`docs/architecture/REALTIME.md`](docs/architecture/REALTIME.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — production deploy and runbook

Service-specific architecture docs:

- [`chat-ws/ARCHITECTURE.md`](chat-ws/ARCHITECTURE.md)
- [`frontend/docs/ARCHITECTURE.md`](frontend/docs/ARCHITECTURE.md)
