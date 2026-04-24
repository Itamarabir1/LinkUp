#!/usr/bin/env bash
set -euo pipefail

echo "[smoke] checking pgbouncer container health"
docker compose ps pgbouncer

echo "[smoke] waiting for pgbouncer to become healthy"
for i in {1..30}; do
  status="$(docker inspect -f '{{.State.Health.Status}}' linkup_pgbouncer 2>/dev/null || true)"
  if [[ "$status" == "healthy" ]]; then
    break
  fi
  sleep 2
done

final_status="$(docker inspect -f '{{.State.Health.Status}}' linkup_pgbouncer)"
if [[ "$final_status" != "healthy" ]]; then
  echo "[smoke][error] pgbouncer is not healthy: $final_status"
  exit 1
fi

echo "[smoke] SHOW POOLS via pgbouncer admin"
if [[ -z "${PGB_ADMIN_PASSWORD:-}" ]]; then
  echo "[smoke][error] set PGB_ADMIN_PASSWORD before running this script"
  exit 1
fi
docker compose exec -T pgbouncer sh -lc \
  "PGPASSWORD=$PGB_ADMIN_PASSWORD psql -h 127.0.0.1 -p 6432 -U pgbouncer_admin pgbouncer -c 'SHOW POOLS;'"
docker compose exec -T pgbouncer sh -lc \
  "PGPASSWORD=$PGB_ADMIN_PASSWORD psql -h 127.0.0.1 -p 6432 -U pgbouncer_admin pgbouncer -c 'SHOW SERVERS;'"

echo "[smoke] backend health endpoint"
curl -fsS "http://localhost:8000/api/v1/health" >/dev/null

echo "[smoke] done"
