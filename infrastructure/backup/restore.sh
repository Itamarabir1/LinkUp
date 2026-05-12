#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# LinkUp PostgreSQL restore – S3 → decrypt → pg_restore
#
# Usage:
#   restore.sh                          # restores the latest daily backup
#   restore.sh daily/2026-05-12_03-00-00_linkup_app.dump.enc
#   restore.sh --list                   # list available backups
#
# Required env:
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   PGHOST, PGPORT
#   S3_BUCKET, BACKUP_ENCRYPTION_KEY
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
# ---------------------------------------------------------------------------
set -euo pipefail

RESTORE_DIR="${RESTORE_DIR:-/tmp/restore}"
ENC_FILE="${RESTORE_DIR}/backup.dump.enc"
DUMP_FILE="${RESTORE_DIR}/backup.dump"

log() { echo "[restore] $(date -u +%H:%M:%S) $*"; }

cleanup() {
    rm -f "$ENC_FILE" "$DUMP_FILE"
}
trap cleanup EXIT

# ── Validate required env ──────────────────────────────────────────────────
for var in POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB PGHOST PGPORT \
           S3_BUCKET BACKUP_ENCRYPTION_KEY \
           AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION; do
    if [ -z "${!var:-}" ]; then
        log "ERROR: $var is not set"
        exit 1
    fi
done

mkdir -p "$RESTORE_DIR"

# ── List mode ──────────────────────────────────────────────────────────────
if [ "${1:-}" = "--list" ]; then
    log "Available backups in s3://${S3_BUCKET}:"
    echo ""
    echo "=== Daily ==="
    aws s3 ls "s3://${S3_BUCKET}/daily/" --human-readable 2>/dev/null || echo "  (none)"
    echo ""
    echo "=== Pre-deploy ==="
    aws s3 ls "s3://${S3_BUCKET}/pre-deploy/" --human-readable 2>/dev/null || echo "  (none)"
    exit 0
fi

# ── Resolve S3 key ─────────────────────────────────────────────────────────
if [ -n "${1:-}" ]; then
    S3_KEY="$1"
else
    log "No key specified, finding latest daily backup ..."
    S3_KEY=$(aws s3api list-objects-v2 \
        --bucket "$S3_BUCKET" \
        --prefix "daily/" \
        --query 'sort_by(Contents, &LastModified)[-1].Key' \
        --output text)

    if [ -z "$S3_KEY" ] || [ "$S3_KEY" = "None" ]; then
        log "ERROR: No backups found in s3://${S3_BUCKET}/daily/"
        exit 1
    fi
    log "Latest backup: $S3_KEY"
fi

# ── 1. Download ────────────────────────────────────────────────────────────
log "Downloading s3://${S3_BUCKET}/${S3_KEY} ..."
aws s3 cp "s3://${S3_BUCKET}/${S3_KEY}" "$ENC_FILE" --no-progress

# ── 2. Decrypt ─────────────────────────────────────────────────────────────
log "Decrypting ..."
openssl enc -aes-256-cbc -d -salt -pbkdf2 -iter 100000 \
    -in "$ENC_FILE" \
    -out "$DUMP_FILE" \
    -pass "pass:${BACKUP_ENCRYPTION_KEY}"

# ── 3. Restore ─────────────────────────────────────────────────────────────
log "Restoring into ${POSTGRES_DB} ..."
export PGPASSWORD="$POSTGRES_PASSWORD"

pg_restore \
    --host="$PGHOST" \
    --port="$PGPORT" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --verbose \
    "$DUMP_FILE"

# ── 4. Sanity check — print row counts for key tables ─────────────────────
log "Restore complete. Row counts:"
psql -h "$PGHOST" -p "$PGPORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A <<'SQL'
SELECT tablename || ': ' || n_live_tup
FROM   pg_stat_user_tables
ORDER  BY n_live_tup DESC
LIMIT  15;
SQL

log "Done."
