#!/usr/bin/env bash
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose --env-file backend/.env --env-file frontend/.env}"

echo "[1/6] Verifying required env contract in backend/.env"
grep -E '^FIREBASE_CREDENTIALS_JSON=' backend/.env >/dev/null

echo "[2/6] Recreating Firebase-dependent services"
$COMPOSE --profile prod up -d --no-deps --force-recreate backend notification-worker task-worker ai-worker

echo "[3/6] Verifying backend runtime env"
$COMPOSE exec -T backend sh -c "printenv | grep -E '^FIREBASE_CREDENTIALS_JSON=|^FIREBASE_SERVICE_ACCOUNT_PATH='"

echo "[4/6] Verifying Firebase admin app initialized"
$COMPOSE exec -T backend sh -c "python -c \"import firebase_admin; print(len(firebase_admin._apps))\"" | grep -q '^1$'

echo "[5/6] Verifying backend readiness"
$COMPOSE exec -T backend sh -c "python -c \"import urllib.request;print(urllib.request.urlopen('http://localhost:8000/readyz').read().decode())\"" | grep -q '"status":"healthy"'

echo "[6/6] Verifying chat-ws Redis contract"
$COMPOSE exec -T chat-ws sh -c "printenv | grep -E '^REDIS_URL='" | grep -q 'redis://:.*@redis:6379/1'

echo "OK: Firebase Model B and Redis runtime contracts validated."
