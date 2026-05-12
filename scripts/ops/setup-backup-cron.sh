#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Install (or update) the daily database backup cron job.
# Run once on the EC2 host after initial setup.
#
# Usage:  bash scripts/ops/setup-backup-cron.sh [deploy_dir]
#   deploy_dir  – absolute path to the LinkUp repo (default: ~/LinkUp)
# ---------------------------------------------------------------------------
set -euo pipefail

DEPLOY_DIR="${1:-$HOME/LinkUp}"
CRON_ID="# linkup-db-backup"
LOG_FILE="/var/log/linkup-backup.log"

CRON_LINE="0 3 * * * cd ${DEPLOY_DIR} && docker compose --env-file backend/.env --profile backup run --rm -e BACKUP_TYPE=daily db-backup >> ${LOG_FILE} 2>&1 ${CRON_ID}"

touch "$LOG_FILE" 2>/dev/null || sudo touch "$LOG_FILE" && sudo chmod 666 "$LOG_FILE"

EXISTING=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING" | grep -qF "$CRON_ID"; then
    echo "Updating existing backup cron entry ..."
    UPDATED=$(echo "$EXISTING" | grep -v "$CRON_ID")
    echo "${UPDATED}
${CRON_LINE}" | crontab -
else
    echo "Adding new backup cron entry ..."
    echo "${EXISTING}
${CRON_LINE}" | crontab -
fi

echo "Cron installed. Verify with:  crontab -l"
echo "Logs will go to: ${LOG_FILE}"
echo ""
echo "To trigger a manual backup:"
echo "  cd ${DEPLOY_DIR} && docker compose --env-file backend/.env --profile backup run --rm -e BACKUP_TYPE=daily db-backup"
