# Kubernetes (LinkUp)

Manifests under `k8s/` match [docker-compose.yml](../docker-compose.yml) and [backend/app/core/config.py](../backend/app/core/config.py).

## GKE production (Cloud SQL + Memorystore)

Use overlay **[overlays/gke-prod](overlays/gke-prod/)** instead of in-cluster Postgres/Redis: Cloud SQL Auth Proxy sidecar, nginx Ingress + cert-manager unchanged, Workload Identity, and Secret layout for Memorystore **`REDIS_URL`**. See [overlays/gke-prod/README.md](overlays/gke-prod/README.md). Build with:

`kubectl kustomize k8s/overlays/gke-prod --load-restrictor LoadRestrictionsNone`

## Deploy order

1. Create namespace: `kubectl apply -f k8s/base/namespace.yaml`
2. Create **Secrets** (see below).
3. `kubectl apply -k k8s/infra` — Postgres, Redis, RabbitMQ, infra ConfigMaps.
4. **Migrations** (one-off Job; delete old job before re-run):

   ```bash
   kubectl delete job linkup-migrate -n linkup --ignore-not-found
   kubectl apply -f k8s/infra/migrate-job.yaml
   kubectl wait --for=condition=complete job/linkup-migrate -n linkup --timeout=300s
   ```

5. `kubectl apply -k k8s/email-renderer` — Node/React Email render API (backend + worker call it).
6. `kubectl apply -k k8s/backend`, `k8s/chat-ws`, `k8s/worker`, `k8s/frontend` (or `kubectl apply -k k8s/base` — includes `email-renderer` before `backend`).

If you apply overlays individually, start **email-renderer** before **backend** / **worker** so outbound email rendering can reach `EMAIL_RENDERER_URL` ([backend/configmap.yaml](backend/configmap.yaml)).

## Environment variable names (backend)

Pydantic loads DB/Redis from **`DATABASE_URL_RAW`** and **`REDIS_URL_RAW`** (not `DATABASE_URL` / `REDIS_URL`). Deployments map Secret keys `DATABASE_URL` / `REDIS_URL` → those env names so existing secrets can keep the same key names.

## ConfigMap highlights

- **`UVICORN_WORKERS`**: used by ConfigMap; production image maps **`WORKERS`** from this value in [backend/deployment.yaml](backend/deployment.yaml).
- **`AWS_REGION`**: set to `eu-north-1` in [backend/configmap.yaml](backend/configmap.yaml) — **must match your S3 bucket region** ([backend/.env.example](../backend/.env.example) shows `eu-central-1` as the repo default; change ConfigMap if your bucket is elsewhere).
- **`S3_BUCKET_NAME`**: empty in repo — set a real bucket name before relying on uploads.
- **`SENTRY_DSN`**: empty disables Sentry (optional).
- **Redis**: one Deployment, logical **DB 0** (API) and **DB 1** (chat / completion) — same model as Docker Compose.
- **`EMAIL_RENDERER_URL`**: Cluster DNS to the email-renderer Service (`http://linkup-email-renderer:3001`). Image: `ghcr.io/.../linkup-email-renderer:latest` (build/push via [email-renderer CI](../.github/workflows/email-renderer-ci.yml)).

## Secrets to create manually

Replace placeholder values. Namespace: `linkup`.

### 1. GHCR pull (`ghcr-secret`)

```bash
kubectl create secret docker-registry ghcr-secret \
  --namespace linkup \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USER \
  --docker-password=YOUR_GHCR_TOKEN \
  --docker-email=YOUR_EMAIL
```

### 2. Postgres (`linkup-db-secret`)

Keys: `username`, `password` — referenced by [infra/postgres.yaml](infra/postgres.yaml).

```bash
kubectl create secret generic linkup-db-secret \
  --namespace linkup \
  --from-literal=username=admin \
  --from-literal=password='YOUR_DB_PASSWORD'
```

### 3. Redis (`linkup-redis-secret`)

Key: `password` — must match the password embedded in **`REDIS_URL`** for backend/chat-ws if you use `redis://:password@host:6379/...`.

```bash
kubectl create secret generic linkup-redis-secret \
  --namespace linkup \
  --from-literal=password='YOUR_REDIS_PASSWORD'
```

### 4. RabbitMQ (`linkup-rabbitmq-secret`)

Key: `password` — must match [infra/configmap.yaml](infra/configmap.yaml) user `guest` unless you change the ConfigMap.

```bash
kubectl create secret generic linkup-rabbitmq-secret \
  --namespace linkup \
  --from-literal=password='YOUR_RABBITMQ_PASSWORD'
```

### 5. Backend / worker (`linkup-backend-secret`)

Keys used by deployments:

| Key | Purpose |
|-----|---------|
| `DATABASE_URL` | Full async URL (e.g. `postgresql+asyncpg://user:pass@linkup-db:5432/linkup_app`) — mapped to `DATABASE_URL_RAW` |
| `REDIS_URL` | e.g. `redis://:password@linkup-redis:6379/0` — mapped to `REDIS_URL_RAW` |
| `SECRET_KEY` | JWT; same logical secret as chat-ws `JWT_SECRET` |
| `RABBITMQ_PASSWORD` | |
| `BREVO_API_KEY` | |
| `GOOGLE_MAPS_API_KEY` | |
| `GOOGLE_CLIENT_ID` | |
| `AWS_ACCESS_KEY_ID` | |
| `AWS_SECRET_ACCESS_KEY` | |
| `FIREBASE_CREDENTIALS_JSON` | JSON string (or leave empty if unused) — see [firebase.py](../backend/app/infrastructure/firebase_core/firebase.py) |

```bash
kubectl create secret generic linkup-backend-secret \
  --namespace linkup \
  --from-literal=DATABASE_URL='postgresql+asyncpg://USER:PASS@linkup-db:5432/linkup_app' \
  --from-literal=REDIS_URL='redis://:REDIS_PASS@linkup-redis:6379/0' \
  --from-literal=SECRET_KEY='YOUR_JWT_SECRET' \
  --from-literal=RABBITMQ_PASSWORD='...' \
  --from-literal=BREVO_API_KEY='...' \
  --from-literal=GOOGLE_MAPS_API_KEY='...' \
  --from-literal=GOOGLE_CLIENT_ID='...' \
  --from-literal=AWS_ACCESS_KEY_ID='...' \
  --from-literal=AWS_SECRET_ACCESS_KEY='...' \
  --from-literal=FIREBASE_CREDENTIALS_JSON=''
```

### 6. Chat-ws (`linkup-chat-ws-secret`)

Keys: `REDIS_URL` (typically `.../1` for chat DB), `JWT_SECRET` (must equal `SECRET_KEY`).

```bash
kubectl create secret generic linkup-chat-ws-secret \
  --namespace linkup \
  --from-literal=REDIS_URL='redis://:REDIS_PASS@linkup-redis:6379/1' \
  --from-literal=JWT_SECRET='SAME_AS_SECRET_KEY'
```

## Optional

- **Ingress** ([backend/ingress.yaml](backend/ingress.yaml)): requires an ingress controller; adjust `ingressClassName`, TLS, and cert-manager `ClusterIssuer` to your cluster.
- **TLS secret** `linkup-tls`: created by cert-manager when using the annotation, or create manually.
- **Stable public media URLs:** if you use CloudFront in front of the same S3 bucket as the API, set **`CLOUDFRONT_DOMAIN`** (hostname only, no `https://`) on the backend Deployment — same semantics as `backend/.env` / `Settings` in [`backend/app/core/config.py`](../backend/app/core/config.py). When unset, the API falls back to presigned S3 GET for avatars/group images.

## Files not in `kubectl apply -k` by default

- **`k8s/infra/migrate-job.yaml`** — apply manually when you need migrations (see Deploy order).
