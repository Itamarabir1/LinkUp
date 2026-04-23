#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "alembic.ini" ]]; then
  echo "[check-migration-head] run from backend/ directory"
  exit 1
fi

out="$(uv run alembic current)"
echo "$out"

if ! grep -q "(head)" <<<"$out"; then
  echo "[check-migration-head][error] alembic current is not at head"
  exit 1
fi

echo "[check-migration-head] current revision is head"

