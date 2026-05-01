# Deployment Guide

This document is the operational source of truth for Linkup production deployment on EC2.

Related operations docs:

- [`docs/operations/RUNBOOK.md`](operations/RUNBOOK.md)
- [`docs/operations/MONITORING.md`](operations/MONITORING.md)

## Production Topology

- **Host:** single EC2 instance.
- **Runtime:** Docker Compose (`--profile prod`).
- **Ingress:** `nginx` reverse proxy with TLS termination.
- **Images:** pulled from GHCR (`ghcr.io/<owner>/linkup/*`).
- **Public URL:** `https://linkup.itamarabir.com`.

### Main runtime services

- `backend` (FastAPI)
- `chat-ws` (Go WebSocket service)
- `frontend` (Nginx static app)
- `nginx` (edge reverse proxy)
- `notification-worker`, `task-worker`, `ai-worker`
- Infra: `db`, `pgbouncer`, `rabbitmq`, `redis-primary`, `redis-replica`, `redis-sentinel`

## CI/CD Flow (GitHub Actions)

Deploy pipeline lives in `.github/workflows/backend-ci.yml`.

### High-level flow

1. Run lint + tests + migrations.
2. Build and push images to GHCR.
3. SSH to EC2 (`appleboy/ssh-action`).
4. Pull latest git + sync env files.
5. Pull images from GHCR.
6. Bring up infra, then app services in order.
7. Health-gated backend rollout (`docker compose ... up --wait`).
8. Roll back backend image on health failure.

### Rollback behavior

- Previous backend image tag is stored in `.deploy_state/backend_prev_tag`.
- If new backend fails health gate, deploy re-runs backend with previous image.
- If rollback also fails, workflow exits with manual intervention required.

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
- `frontend/.env` provides `VITE_*` + `APP_ENV` for frontend runtime rendering.
- `chat-ws/.env` contains chat-ws specific env values.
- Deploy script enforces backend/frontend env presence and fails fast when missing.

## Frontend Runtime Config (No build-time secrets)

Frontend is environment-agnostic at image build time.

### How it works

1. Frontend image is built without `VITE_*` injection.
2. At container startup, `frontend/docker/40-render-config.sh` runs.
3. Script uses `envsubst` to render:
   - `/usr/share/nginx/html/config.js` from `frontend/docker/config.template.js`
   - `/usr/share/nginx/html/firebase-messaging-sw.js` from `frontend/docker/firebase-messaging-sw.template.js`
4. App reads `window.__APP_CONFIG__` via `frontend/src/config/runtime.ts`.
5. Dev fallback remains `import.meta.env` (through `frontend/public/config.js` stub).

This allows the same frontend image to run in all environments.

## Deploy Runbook

### Standard deploy

Triggered by push to `main` (backend workflow path filters apply).

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
