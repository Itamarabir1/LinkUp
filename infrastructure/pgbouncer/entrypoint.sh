#!/usr/bin/env sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${PGBOUNCER_ADMIN_PASSWORD:?PGBOUNCER_ADMIN_PASSWORD is required}"

OUT="/var/lib/pgbouncer/userlist.txt"
envsubst < /etc/pgbouncer/userlist.txt.template > "$OUT"
chmod 600 "$OUT"

exec pgbouncer /etc/pgbouncer/pgbouncer.ini
