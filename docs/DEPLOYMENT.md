# Deployment Guide

This document is the operational source of truth for Linkup production deployment on EC2.

Related operations docs:

- [`docs/operations/RUNBOOK.md`](operations/RUNBOOK.md)
- [`docs/operations/MONITORING.md`](operations/MONITORING.md) — כולל [קונסולות פרודקשן Sentry + Better Stack](operations/MONITORING.md#external-dashboards-production)

## Production Topology

- **Host:** single EC2 instance.
- **Runtime:** Docker Compose (`--profile prod`).
- **Ingress:** `nginx` reverse proxy with TLS termination.
- **Images:** נמשכות מ-GHCR — ברירות מחדל ב־**`docker-compose.yml`**: `ghcr.io/<owner>/linkup/{backend,worker,migrate,pgbouncer,frontend,chat-ws}` וגם **`ghcr.io/<owner>/linkup-email-renderer`** (שירות נפרד בלי קידומת `linkup/`).
- **Public URL:** `https://linkup.itamarabir.com`.

### Main runtime services

- `backend` (FastAPI)
- `chat-ws` (Go WebSocket service)
- `frontend` (Nginx static app)
- `nginx` (edge reverse proxy)
- `email-renderer` (Node — React Email **`POST /render`**)
- `notification-worker`, `task-worker`, `ai-worker`
- `migrate` — Job חד־פעמי (`alembic upgrade head`) לפני עליית ה-API וה-workers
- Infra: `db`, `pgbouncer`, `rabbitmq`, `redis`

## CI/CD Flow (GitHub Actions)

Service workflows (**Backend CI**, **Frontend CI**, **Chat-WS CI**, **Email renderer CI**) lint, test, and **push images to GHCR** when their path filters match and the run is on `main`.

Production deploy is centralized in **`deploy-ec2.yml`**, triggered by **`workflow_run`** after **any** of those four workflows completes **successfully** on `main` (same commit). **Concurrency** group `ec2-deploy-production` with **`cancel-in-progress: false`** queues overlapping runs so only one deploy executes at a time.

| Workflow | When it runs | What it does |
|----------|----------------|--------------|
| [`backend-ci.yml`](../.github/workflows/backend-ci.yml) | Push/PR with path filters for backend, infra, nginx, compose, or this workflow file | Lint, tests, migrations, Docker build → push **`backend`**, **`worker`**, **`migrate`**, **`pgbouncer`** to GHCR on push to `main` (does **not** deploy by itself). |
| [`deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml) | After **Backend CI**, **Frontend CI**, **Chat-WS CI**, or **Email renderer CI** completes successfully on `main` (`workflow_run`) | Full stack on EC2: git sync, env sync, `envsubst` for edge **`nginx/nginx.conf`**, pull GHCR images, bring up infra → migrate → app services → **`frontend` + `nginx`**, **smokes** (`config.js` in **`linkup_frontend`**, `/health` in **`linkup_email_renderer`**) **before** backend rollout gate, health-gated backend deploy (`/readyz`, Firebase env, public `/livez` + `/config.js`), write resolved backend tag to **`.deploy_state/backend_prev_tag`**, rollback on failure. |

### Deploy (`deploy-ec2.yml`) — high-level flow

1. SSH to EC2 (`appleboy/ssh-action`); image tag = triggering workflow’s **`head_sha`** (fallback to **`backend:latest`** if that tag is missing from GHCR).
2. Pull latest git + sync `*.env.production` → compose env files; sync **`JWT_SECRET`** in **`chat-ws/.env`** from **`SECRET_KEY`**. Render **`nginx/nginx.conf`** from template using **`SENTRY_REPORT_URI`** from **`backend/.env`**.
3. Pull images from GHCR (backend prefers the workflow commit SHA tag, then **`…/backend:latest`** if that tag is absent).
4. Bring up infra (`db`, single persistent Redis, RabbitMQ), **`pgbouncer`**, run **`migrate`**, then **`email-renderer`**, workers, **`chat-ws`**, **`frontend` + `nginx`** (force-recreate **`nginx`** when nginx/frontend-related files changed in `HEAD`).
5. **Smoke** from inside containers: **`linkup_frontend`** → **`http://localhost:80/config.js`**, **`linkup_email_renderer`** → **`http://localhost:3001/health`**.
6. Roll out **`backend`** with **`--wait`**, then run mandatory checks (Firebase, Redis URL in **`chat-ws`**, **`/readyz`**, public **`/livez`** and **`/config.js`** through TLS).
7. On failure: roll back **`backend`** to the previous tag from **`.deploy_state/backend_prev_tag`**; if **`docker pull`** for that image fails (e.g. old digest removed), fall back to **`…/backend:latest`**.

### Rollback behavior

- After a successful deploy, the resolved backend image **tag** (commit SHA or `latest`) is stored in **`.deploy_state/backend_prev_tag`**.
- If the new backend fails the post-rollout gate, the script switches **`backend`** back to the previous image; if **`docker pull`** for that ref fails, it pulls the **`backend:latest`** image for the same GHCR repository instead.
- If rollback **`compose up`** for **`backend`** still fails, the workflow exits for manual intervention.

## Environment Files (.env.production)

These files are expected on the EC2 host under `~/LinkUp/` and are **not committed**:

- `backend/.env.production`
- `chat-ws/.env.production`
- `frontend/.env.production`

During deploy, they are copied to:

- `backend/.env`
- `chat-ws/.env`
- `frontend/.env`

Then compose uses:

```bash
docker compose --env-file backend/.env --env-file frontend/.env
```

Notes:

- `backend/.env` drives backend + infrastructure variables (Postgres/Redis/RabbitMQ/etc.).
- `frontend/.env` provides `VITE_*` + `APP_ENV` for frontend runtime rendering. In **`docker-compose.yml`**, the **`frontend`** service (profile **`prod`**) lists **`env_file: ./frontend/.env`** so the static container receives the same contract as local/EC2 deploys that use **`--env-file frontend/.env`**; without a file at that path, Compose may fail to start the service — keep a file (even a stub) or adjust paths for your environment.
- `chat-ws/.env` contains chat-ws specific env values.
- Deploy script enforces backend/frontend env presence and fails fast when missing.
- **Edge nginx:** CI renders **`nginx/nginx.conf`** from **`nginx/nginx.conf.template`** with `envsubst '${SENTRY_REPORT_URI}'`, reading **`SENTRY_REPORT_URI`** from **`backend/.env`** (same as local: **`bash scripts/ops/render-nginx-conf.sh`**). **PgBouncer:** no host-side `userlist.txt` generation; container startup renders `/var/lib/pgbouncer/userlist.txt` from `POSTGRES_USER` / `POSTGRES_PASSWORD` / `PGBOUNCER_ADMIN_PASSWORD`.

## Frontend Runtime Config (No build-time secrets)

Frontend is environment-agnostic at image build time.

### How it works

1. Frontend image is built without `VITE_*` injection.
2. At container startup, `frontend/docker/40-render-config.sh` runs (`#!/bin/sh`, `set -e`). **Fail-fast:** the script exits non-zero if any of these are unset or empty: `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_MESSAGING_SENDER_ID`, `VITE_FIREBASE_VAPID_KEY`. **Defaults for optional vars:** `APP_ENV` defaults to `production`, `VITE_API_TIMEOUT_MS` to `30000`, `VITE_GOOGLE_MAPS_MAP_ID` to empty — see the script for the full substitution list.
3. Script uses `envsubst` to render:
   - `/usr/share/nginx/html/config.js` from `frontend/docker/config.template.js`
   - `/usr/share/nginx/html/firebase-messaging-sw.js` from `frontend/docker/firebase-messaging-sw.template.js`
4. App reads `window.__APP_CONFIG__` via `frontend/src/config/runtime.ts`.
5. Dev fallback remains `import.meta.env` (through `frontend/public/config.js` stub).

This allows the same frontend image to run in all environments.

## Deploy Runbook

### Standard deploy

- **Full stack:** after **Backend CI**, **Frontend CI**, **Chat-WS CI**, or **Email renderer CI** succeeds on **`main`**, **`deploy-ec2.yml`** runs (queued if another deploy is in flight). Any green service CI on `main` can drive a full compose rollout so frontend-only or chat-only changes still refresh EC2 without relying on **backend-ci** path filters.

After deploy:

```bash
docker compose ps
docker logs linkup_backend --tail 100
docker logs linkup_frontend --tail 100
```

Post-deploy security headers check (recommended):

```bash
curl -I https://linkup.itamarabir.com | grep -E "HTTP|strict|x-content|x-frame|referrer|permissions|content-security-policy"
```

For CSP policy (enforcing header, `script-src` without `'unsafe-inline'` and **`/bootstrap.js`** shell, allowlists, `report-uri`, SPA caveats, optional rollback via Report-Only), see [`docs/SECURITY_HEADERS.md`](SECURITY_HEADERS.md).

### Validate frontend runtime config

```bash
docker exec linkup_frontend env | grep VITE_FIREBASE_PROJECT_ID
docker exec linkup_frontend sh -lc "grep -n 'projectId' /usr/share/nginx/html/config.js"
```

Expected: real value (for example `link-up-d33dc`), not `${VITE_FIREBASE_PROJECT_ID}`.

## Common Issues Runbook

### 1) Disk full on EC2

Symptoms:

- image pulls fail
- deploy fails before or during compose up

Checks:

```bash
df -h
docker system df
```

Cleanup:

```bash
docker image prune -af
docker container prune -f
docker volume prune -f
```

### 2) RabbitMQ reset / consumer instability

Symptoms:

- workers stop consuming
- queue iterator closes / reconnect loops

Actions:

```bash
docker logs linkup_notification_worker --tail 200
docker logs linkup_task_worker --tail 200
docker logs linkup_ai_worker --tail 200
docker logs linkup_rabbitmq --tail 200
```

Then restart affected workers:

```bash
docker compose up -d --no-deps notification-worker task-worker ai-worker
```

If needed, inspect/replay DLQ via project ops scripts.

### 3) JWT mismatch (`backend` vs `chat-ws`)

Symptoms:

- chat websocket auth fails
- token accepted by backend but rejected by chat-ws

Current protection:

- deploy script syncs `JWT_SECRET` in `chat-ws/.env` from `SECRET_KEY` in `backend/.env` (single source of truth).

Manual verification:

```bash
grep -E '^SECRET_KEY=' ~/LinkUp/backend/.env
grep -E '^JWT_SECRET=' ~/LinkUp/chat-ws/.env
```

Values must match.

## One-time / maintenance updates

### Update frontend public config values

1. Edit `~/LinkUp/frontend/.env.production`.
2. Redeploy (or restart frontend container).

### Rotate backend secrets

1. Edit `~/LinkUp/backend/.env.production`.
2. Redeploy.

### Keep chat-ws secret aligned

No manual step required if deploy runs normally; sync is automatic in deploy script.
