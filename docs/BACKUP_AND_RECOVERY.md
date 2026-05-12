# Database Backup & Recovery

## Overview

LinkUp uses an automated backup pipeline that creates encrypted PostgreSQL dumps
and stores them in S3. Backups run on two triggers:

| Trigger | Schedule | S3 prefix | Retention |
|---------|----------|-----------|-----------|
| **Daily cron** | 03:00 UTC | `daily/` | 30 days (Glacier after 14d) |
| **Pre-deploy** | Before every CI deploy | `pre-deploy/` | 90 days (Glacier after 30d) |

**Backup flow:** `pg_dump --format=custom --compress=6` → AES-256-CBC encryption → S3 upload → verify.

## Architecture

```
┌─────────────── EC2 Instance ───────────────┐
│                                            │
│  Host crontab (03:00 UTC)                  │
│       │                                    │
│       ▼                                    │
│  docker compose --profile backup run ...   │
│       │                                    │
│  ┌────▼─────────────────────┐              │
│  │  db-backup container     │              │
│  │  pg_dump → encrypt → S3  │──────────┐   │
│  └────┬─────────────────────┘          │   │
│       │ direct connection              │   │
│  ┌────▼───────────┐                    │   │
│  │  PostgreSQL 15 │                    │   │
│  └────────────────┘                    │   │
└────────────────────────────────────────│───┘
                                         │
                          ┌──────────────▼──────────────┐
                          │  S3: linkup-db-backups      │
                          │  ├── daily/                 │
                          │  │   └── 2026-05-12_...enc  │
                          │  └── pre-deploy/            │
                          │      └── 2026-05-12_...enc  │
                          └─────────────────────────────┘
```

## Setup (one-time)

### 1. Generate an encryption key

```bash
openssl rand -base64 32
```

Store the result in `backend/.env.production` as `BACKUP_ENCRYPTION_KEY`.

**CRITICAL:** Store this key separately from the backups (e.g. in a password
manager or AWS Secrets Manager). Without it, encrypted backups are useless.

### 2. Create the S3 bucket

```bash
aws s3 mb s3://linkup-db-backups --region eu-central-1

aws s3api put-public-access-block \
  --bucket linkup-db-backups \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-lifecycle-configuration \
  --bucket linkup-db-backups \
  --lifecycle-configuration file://infrastructure/backup/s3-lifecycle.json
```

### 3. Configure environment variables

Add to `backend/.env.production` on the EC2 host:

```
BACKUP_S3_BUCKET=linkup-db-backups
BACKUP_ENCRYPTION_KEY=<key from step 1>
```

AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`)
should already be set for the S3 media upload feature.

### 4. Install the daily cron job

```bash
ssh ec2-host
bash ~/LinkUp/scripts/ops/setup-backup-cron.sh
```

Verify: `crontab -l` should show the `linkup-db-backup` entry.

### 5. Build the backup image

```bash
cd ~/LinkUp
docker compose --env-file backend/.env build db-backup
```

## Manual Backup

```bash
cd ~/LinkUp

# Daily backup
docker compose --env-file backend/.env --profile backup run --rm \
  -e BACKUP_TYPE=daily db-backup

# Pre-deploy backup
docker compose --env-file backend/.env --profile backup run --rm \
  -e BACKUP_TYPE=pre-deploy db-backup
```

## Restore Procedure

### List available backups

```bash
docker compose --env-file backend/.env --profile backup run --rm \
  --entrypoint /usr/local/bin/restore.sh db-backup --list
```

### Restore the latest daily backup

```bash
# 1. Stop services that write to the database
docker compose stop backend notification-worker task-worker ai-worker

# 2. Restore
docker compose --env-file backend/.env --profile backup run --rm \
  --entrypoint /usr/local/bin/restore.sh db-backup

# 3. Run migrations (in case backup predates latest schema)
docker compose run --rm migrate

# 4. Restart services
docker compose --env-file backend/.env up -d backend notification-worker task-worker ai-worker
```

### Restore a specific backup

```bash
docker compose --env-file backend/.env --profile backup run --rm \
  --entrypoint /usr/local/bin/restore.sh db-backup \
  "daily/2026-05-12_03-00-00_linkup_app.dump.enc"
```

## Disaster Recovery: Full EC2 Rebuild

If the EC2 instance is lost entirely:

1. **Launch a new EC2 instance** with the same security group and IAM role.

2. **Install Docker + Docker Compose** (see existing deploy docs).

3. **Clone the repository:**
   ```bash
   git clone https://github.com/ItamarAbir1/LinkUp.git ~/LinkUp
   cd ~/LinkUp
   ```

4. **Restore secrets:** Copy `backend/.env.production`, `chat-ws/.env.production`,
   and `frontend/.env.production` from your secrets store.

5. **Start the database:**
   ```bash
   cp backend/.env.production backend/.env
   docker compose --env-file backend/.env up -d db
   docker compose --env-file backend/.env exec db \
     psql -U admin -c "CREATE DATABASE linkup_app;"
   ```

6. **Restore from backup:**
   ```bash
   docker compose --env-file backend/.env build db-backup
   docker compose --env-file backend/.env --profile backup run --rm \
     --entrypoint /usr/local/bin/restore.sh db-backup
   ```

7. **Run migrations and start the full stack:**
   ```bash
   docker compose --env-file backend/.env run --rm migrate
   docker compose --env-file backend/.env --profile prod up -d
   ```

8. **Update DNS** to point to the new instance IP.

9. **Re-install the backup cron:**
   ```bash
   bash scripts/ops/setup-backup-cron.sh
   ```

## Monitoring

Check backup health (exit code 0 = healthy, 1 = stale/missing):

```bash
# On the EC2 host (needs AWS credentials in env)
export BACKUP_S3_BUCKET=linkup-db-backups
bash scripts/ops/check-backup-health.sh
```

The health check verifies:
- A daily backup exists in S3
- The most recent backup is less than 25 hours old
- The backup file is above the minimum size threshold (not empty/corrupt)

## Backup Verification

Periodically test that backups are actually restorable:

```bash
# Spin up a throwaway postgres container
docker run -d --name verify_db \
  -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=test -e POSTGRES_DB=linkup_app \
  postgis/postgis:15-3.3

# Wait for it to be ready
sleep 5

# Run restore against the throwaway container
docker compose --env-file backend/.env --profile backup run --rm \
  -e PGHOST=verify_db \
  --entrypoint /usr/local/bin/restore.sh db-backup

# Clean up
docker rm -f verify_db
```

## File Reference

| File | Purpose |
|------|---------|
| `infrastructure/backup/Dockerfile` | Backup container image (postgres:15 + AWS CLI + openssl) |
| `infrastructure/backup/backup.sh` | Core backup script (pg_dump → encrypt → S3) |
| `infrastructure/backup/restore.sh` | Restore script (S3 → decrypt → pg_restore) |
| `infrastructure/backup/s3-lifecycle.json` | S3 retention/lifecycle rules |
| `scripts/ops/setup-backup-cron.sh` | Installs the daily cron job on the host |
| `scripts/ops/check-backup-health.sh` | Checks backup freshness in S3 |
| `docker-compose.yml` (`db-backup` service) | Docker Compose service definition |
| `.github/workflows/deploy-ec2.yml` | Pre-deploy backup trigger |
