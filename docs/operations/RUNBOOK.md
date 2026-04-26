# Operations Runbook

This runbook covers high-frequency production incidents for `https://linkup.itamarabir.com`.

Primary deployment reference: [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md).

## 1) Disk Full on EC2

### Symptoms

- CI deploy fails during `docker pull` / `docker compose up`
- `no space left on device`

### Checks

```bash
df -h
docker system df
```

### Actions

```bash
docker image prune -af
docker container prune -f
docker volume prune -f
```

Re-run deploy after cleanup.

## 2) RabbitMQ Consumer Stops / Keeps Restarting

### Symptoms

- queue backlog grows
- notifications not sent
- repeated consumer restart logs

### Checks

```bash
docker logs linkup_notification_worker --tail 200
docker logs linkup_task_worker --tail 200
docker logs linkup_ai_worker --tail 200
docker logs linkup_rabbitmq --tail 200
```

### Actions

```bash
docker compose up -d --no-deps notification-worker task-worker ai-worker
```

If DLQ depth is high, use replay tooling:

```bash
python scripts/ops/rabbitmq-dlq-replay.py --dry-run
python scripts/ops/rabbitmq-dlq-replay.py --queue notifications_queue --limit 50
```

## 3) JWT Mismatch (backend vs chat-ws)

### Symptoms

- backend auth passes but chat websocket auth fails

### Checks

```bash
grep -E '^SECRET_KEY=' ~/LinkUp/backend/.env
grep -E '^JWT_SECRET=' ~/LinkUp/chat-ws/.env
```

Values must match.

### Prevention

Deploy script syncs `JWT_SECRET` from backend `SECRET_KEY` automatically in `backend-ci.yml`.

## 4) Backend Healthcheck Fails During Deploy

### Symptoms

- backend replacement fails health gate
- rollback triggered in CI

### Checks

```bash
docker logs linkup_backend --tail 200
docker compose ps
```

### Known causes

- missing env values
- DB or PgBouncer unhealthy
- Redis/RabbitMQ unavailable
- HTTPS redirect blocking local health path (fixed via loopback bypass)

### Actions

- validate `backend/.env` exists and contains required keys
- validate `docker compose ... up --wait` status of dependencies
- rerun deploy after root cause fix

## 5) Frontend Runtime Config Missing (`projectId` / OAuth popup issues)

### Symptoms

- `FirebaseError: Missing App configuration value: "projectId"`
- Google OAuth popup `postMessage` blocked by COOP policy

### Checks

```bash
docker exec linkup_frontend env | grep VITE_FIREBASE_PROJECT_ID
docker exec linkup_frontend sh -lc "grep -n 'projectId' /usr/share/nginx/html/config.js"
```

### Actions

- ensure `frontend/.env.production` exists on EC2 and is copied to `frontend/.env` by deploy
- ensure compose uses both env files:
  - `--env-file backend/.env`
  - `--env-file frontend/.env`
- verify nginx sends COOP/COEP headers for OAuth popup compatibility

