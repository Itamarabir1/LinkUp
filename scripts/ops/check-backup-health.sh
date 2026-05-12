#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Check the freshness of the latest database backup in S3.
# Exits 0 if a backup younger than MAX_AGE_HOURS exists, 1 otherwise.
#
# Usage:  bash scripts/ops/check-backup-health.sh
#
# Required env:
#   S3_BUCKET (or BACKUP_S3_BUCKET)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION (or AWS_REGION)
#
# Optional env:
#   MAX_AGE_HOURS  – alert threshold (default: 25)
#   MIN_SIZE_BYTES – minimum expected backup size (default: 1024)
# ---------------------------------------------------------------------------
set -euo pipefail

S3_BUCKET="${S3_BUCKET:-${BACKUP_S3_BUCKET:-}}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-eu-central-1}}"
export AWS_DEFAULT_REGION

MAX_AGE_HOURS="${MAX_AGE_HOURS:-25}"
MIN_SIZE_BYTES="${MIN_SIZE_BYTES:-1024}"

if [ -z "$S3_BUCKET" ]; then
    echo "FAIL: S3_BUCKET / BACKUP_S3_BUCKET is not set"
    exit 1
fi

LATEST=$(aws s3api list-objects-v2 \
    --bucket "$S3_BUCKET" \
    --prefix "daily/" \
    --query 'sort_by(Contents, &LastModified)[-1]' \
    --output json 2>/dev/null)

if [ -z "$LATEST" ] || [ "$LATEST" = "null" ]; then
    echo "FAIL: No daily backups found in s3://${S3_BUCKET}/daily/"
    exit 1
fi

LAST_KEY=$(echo "$LATEST" | python3 -c "import sys,json; print(json.load(sys.stdin)['Key'])")
LAST_SIZE=$(echo "$LATEST" | python3 -c "import sys,json; print(json.load(sys.stdin)['Size'])")
LAST_MODIFIED=$(echo "$LATEST" | python3 -c "import sys,json; print(json.load(sys.stdin)['LastModified'])")

LAST_EPOCH=$(date -d "$LAST_MODIFIED" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${LAST_MODIFIED%%.*}" +%s)
NOW_EPOCH=$(date +%s)
AGE_HOURS=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))

echo "Latest backup: $LAST_KEY"
echo "Size:          $(( LAST_SIZE / 1024 / 1024 )) MB ($LAST_SIZE bytes)"
echo "Age:           ${AGE_HOURS}h (threshold: ${MAX_AGE_HOURS}h)"

FAILED=0

if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
    echo "FAIL: Backup is ${AGE_HOURS}h old (exceeds ${MAX_AGE_HOURS}h threshold)"
    FAILED=1
fi

if [ "$LAST_SIZE" -lt "$MIN_SIZE_BYTES" ]; then
    echo "FAIL: Backup is only ${LAST_SIZE} bytes (below ${MIN_SIZE_BYTES} minimum)"
    FAILED=1
fi

if [ "$FAILED" -eq 1 ]; then
    exit 1
fi

echo "OK: Backup is healthy"
