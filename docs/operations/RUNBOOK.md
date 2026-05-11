# Operations Runbook

This runbook covers high-frequency production incidents for `https://linkup.itamarabir.com`.

Primary deployment reference: [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md).

## Triage consoles (first look)

- **Application errors / RUM / traces:** [Sentry Issues (14d)](https://itamar-abir.sentry.io/issues/?project=4511256490606592&statsPeriod=14d) — matches env DSN wiring; fuller link table in [`MONITORING.md`](MONITORING.md#external-dashboards-production).
- **External uptime / incident history:** [Better Stack monitors](https://uptime.betterstack.com/team/t520754/monitors) — correlates with public [`GET /livez`](https://linkup.itamarabir.com/livez); sample deep-link: [incident `959204833`](https://uptime.betterstack.com/team/t520754/incidents/959204833).

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
# Caution: -af removes ALL unused images including rollback tags.
# For normal maintenance prefer: docker image prune -f (dangling only).
# Use -af only when disk is critically low and you can re-pull.
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

Deploy script on EC2 syncs `JWT_SECRET` from backend `SECRET_KEY` automatically (see **[`deploy-ec2.yml`](../../.github/workflows/deploy-ec2.yml)**).

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

## 6) Admin Access Redirects to `/my-rides`

### Symptoms

- user opens `/admin` and is redirected to `/my-rides` or `/`
- admin API returns unauthorized/forbidden for the same user

### Checks

```bash
make admin-check EMAIL=user@example.com
```

### Actions

```bash
make admin-grant EMAIL=user@example.com
# or
make admin-revoke EMAIL=user@example.com
```

### Notes

- Admin access in UI is controlled by `user.is_admin`.
- Prefer backend admin endpoints for day-to-day role changes; Makefile commands are an ops fallback.
- Re-login after role change to refresh auth payload.

## 7) Admin Ops / Billing / Audit Pages Show Empty or 403

### Symptoms

- בממשק הווב (Vite) המסלולים **`/admin/ops`**, **`/admin/billing`**, **`/admin/audit`** נטענים אבל הנתונים ריקים / שגיאה (זה לא אותו דבר כמו קידומת ה-API **`/api/v1/admin/...`**)
- backend returns 403 with `Missing admin capability`

### Checks

```bash
docker logs linkup_backend --tail 200 | grep -E "Missing admin capability|admin_audit_log_read|admin_outbox_payload_read"
```

### Actions

- If `ADMIN_CAPABILITIES_JSON` is not configured, all admins have full access by default.
- If configured, ensure the admin email appears in the JSON map with required scopes (e.g. `admin.ops.read`, `admin.billing.read`, `admin.audit.read`).
- Re-login after updating capability configuration.

