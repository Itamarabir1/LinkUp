#!/usr/bin/env bash
# Generate nginx/nginx.conf from nginx/nginx.conf.template using SENTRY_REPORT_URI
# from backend/.env (same contract as EC2 deploy in .github/workflows/backend-ci.yml).
# Run from any cwd. Required before: docker compose --profile prod … when using edge nginx.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="$ROOT/nginx/nginx.conf.template"
OUT="$ROOT/nginx/nginx.conf"
ENV_FILE="${ROOT}/backend/.env"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "ERROR: missing $TEMPLATE" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: backend/.env not found — copy backend/.env.example and set SENTRY_REPORT_URI (CSP report endpoint from Sentry)" >&2
  exit 1
fi

command -v envsubst >/dev/null 2>&1 || { echo "ERROR: envsubst missing (gettext package)" >&2; exit 1; }

SENTRY_REPORT_URI="$(grep -E '^SENTRY_REPORT_URI=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
export SENTRY_REPORT_URI
if [[ -z "${SENTRY_REPORT_URI:-}" ]]; then
  echo "ERROR: SENTRY_REPORT_URI missing or empty in $ENV_FILE" >&2
  exit 1
fi

envsubst '${SENTRY_REPORT_URI}' < "$TEMPLATE" > "$OUT"
chmod 600 "$OUT"
echo "Rendered $OUT (from backend/.env → SENTRY_REPORT_URI)"
