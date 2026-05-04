#!/usr/bin/env bash
# Generate infrastructure/pgbouncer/userlist.txt from userlist.txt.template
# using POSTGRES_* and PGBOUNCER_ADMIN_PASSWORD from backend/.env.
# Same contract as EC2 deploy in .github/workflows/backend-ci.yml.
# Run before docker compose pulls up pgbouncer (see Makefile).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="$ROOT/infrastructure/pgbouncer/userlist.txt.template"
OUT="$ROOT/infrastructure/pgbouncer/userlist.txt"
ENV_FILE="${ROOT}/backend/.env"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "ERROR: missing $TEMPLATE" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: backend/.env not found — copy backend/.env.example and configure Postgres/PgBouncer secrets" >&2
  exit 1
fi

command -v envsubst >/dev/null 2>&1 || { echo "ERROR: envsubst missing (gettext package)" >&2; exit 1; }

POSTGRES_USER="$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
POSTGRES_PASSWORD="$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
PGBOUNCER_ADMIN_PASSWORD="$(grep -E '^PGBOUNCER_ADMIN_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
export POSTGRES_USER POSTGRES_PASSWORD PGBOUNCER_ADMIN_PASSWORD

if [[ -z "${POSTGRES_USER:-}" ]]; then
  echo "ERROR: POSTGRES_USER missing or empty in $ENV_FILE" >&2
  exit 1
fi
if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "ERROR: POSTGRES_PASSWORD missing or empty in $ENV_FILE" >&2
  exit 1
fi
if [[ -z "${PGBOUNCER_ADMIN_PASSWORD:-}" ]]; then
  echo "ERROR: PGBOUNCER_ADMIN_PASSWORD missing or empty in $ENV_FILE" >&2
  exit 1
fi

envsubst < "$TEMPLATE" > "$OUT"
chmod 644 "$OUT"
echo "Rendered $OUT (from backend/.env)"
