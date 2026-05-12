#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# LinkUp PostgreSQL backup – pg_dump → encrypt → S3
#
# Required env:
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   PGHOST, PGPORT              (set by docker-compose service)
#   S3_BUCKET                   (target S3 bucket name)
#   BACKUP_ENCRYPTION_KEY       (AES-256 passphrase)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
#
# Optional env:
#   BACKUP_TYPE  – "daily" (default) | "pre-deploy"
#   BACKUP_DIR   – local staging dir (default: /tmp/backups)
# ---------------------------------------------------------------------------
set -euo pipefail

BACKUP_TYPE="${BACKUP_TYPE:-daily}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/backups}"
TIMESTAMP="$(date -u +%Y-%m-%d_%H-%M-%S)"
DUMP_FILE="${BACKUP_DIR}/${TIMESTAMP}_${POSTGRES_DB}.dump"
ENC_FILE="${DUMP_FILE}.enc"
S3_KEY="${BACKUP_TYPE}/${TIMESTAMP}_${POSTGRES_DB}.dump.enc"
STATUS_FILE="${BACKUP_DIR}/last_backup_status.json"

log() { echo "[backup] $(date -u +%H:%M:%S) $*"; }

cleanup() {
    rm -f "$DUMP_FILE" "$ENC_FILE"
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

mkdir -p "$BACKUP_DIR"

# ── 1. pg_dump ─────────────────────────────────────────────────────────────
log "Starting pg_dump (type=$BACKUP_TYPE) ..."
export PGPASSWORD="$POSTGRES_PASSWORD"

pg_dump \
    --host="$PGHOST" \
    --port="$PGPORT" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --compress=6 \
    --verbose \
    --file="$DUMP_FILE"

DUMP_SIZE=$(stat -c%s "$DUMP_FILE" 2>/dev/null || stat -f%z "$DUMP_FILE")
log "Dump complete: $(( DUMP_SIZE / 1024 / 1024 )) MB"

if [ "$DUMP_SIZE" -lt 1024 ]; then
    log "ERROR: Dump file suspiciously small (${DUMP_SIZE} bytes), aborting"
    exit 1
fi

# ── 2. Encrypt ─────────────────────────────────────────────────────────────
log "Encrypting with AES-256-CBC ..."
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in "$DUMP_FILE" \
    -out "$ENC_FILE" \
    -pass "pass:${BACKUP_ENCRYPTION_KEY}"

ENC_SIZE=$(stat -c%s "$ENC_FILE" 2>/dev/null || stat -f%z "$ENC_FILE")
log "Encrypted: $(( ENC_SIZE / 1024 / 1024 )) MB"

CHECKSUM=$(sha256sum "$ENC_FILE" | awk '{print $1}')

# ── 3. Upload to S3 ───────────────────────────────────────────────────────
log "Uploading to s3://${S3_BUCKET}/${S3_KEY} ..."
aws s3 cp "$ENC_FILE" "s3://${S3_BUCKET}/${S3_KEY}" \
    --storage-class STANDARD_IA \
    --no-progress

# ── 4. Verify upload ──────────────────────────────────────────────────────
REMOTE_SIZE=$(aws s3api head-object \
    --bucket "$S3_BUCKET" \
    --key "$S3_KEY" \
    --query 'ContentLength' \
    --output text)

if [ "$REMOTE_SIZE" != "$ENC_SIZE" ]; then
    log "ERROR: Size mismatch — local=${ENC_SIZE}, remote=${REMOTE_SIZE}"
    exit 1
fi

log "Upload verified (${REMOTE_SIZE} bytes)"

# ── 5. Write status file (used by health check) ───────────────────────────
cat > "$STATUS_FILE" <<EOF
{
  "timestamp": "${TIMESTAMP}",
  "type": "${BACKUP_TYPE}",
  "s3_key": "${S3_KEY}",
  "size_bytes": ${ENC_SIZE},
  "checksum_sha256": "${CHECKSUM}",
  "status": "ok"
}
EOF

log "Backup complete: s3://${S3_BUCKET}/${S3_KEY}"
