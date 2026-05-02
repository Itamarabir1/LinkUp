# GKE production overlay (`gke-prod`)

This overlay targets **Google Kubernetes Engine** with:

- **Cloud SQL (PostgreSQL)** via **Cloud SQL Auth Proxy** sidecar on `linkup-backend`, `linkup-worker`, and Job `linkup-migrate`.
- **Memorystore (Redis)** — not deployed in-cluster; put full URLs in Secrets (`REDIS_URL` / `REDIS_URL_RAW`).
- **RabbitMQ** — still the in-cluster Deployment from `k8s/infra/rabbitmq.yaml`.
- **Ingress** — unchanged from base: **nginx ingress class** + **cert-manager** `ClusterIssuer` (`linkup-ingress` in [k8s/backend/ingress.yaml](../../backend/ingress.yaml)); frontend nginx proxies `/api/v1`, `/ws`, `/presence`.

It **does not** apply `k8s/infra/postgres.yaml` or `redis.yaml` (managed services replace them).

## Prerequisites

1. GKE cluster, VPC, Memorystore, Cloud SQL instance (PostGIS enabled).
2. **Workload Identity**: GCP service account with `roles/cloudsql.client`; bind to Kubernetes SA `linkup-cloudsql`:

   ```bash
   gcloud iam service-accounts create linkup-gke-cloudsql --project=YOUR_PROJECT
   gcloud projects add-iam-policy-binding YOUR_PROJECT \
     --member="serviceAccount:linkup-gke-cloudsql@YOUR_PROJECT.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   gcloud iam service-accounts add-iam-policy-binding \
     linkup-gke-cloudsql@YOUR_PROJECT.iam.gserviceaccount.com \
     --role roles/iam.workloadIdentityUser \
     --member "serviceAccount:YOUR_PROJECT.svc.id.goog[linkup/linkup-cloudsql]"
   kubectl annotate serviceaccount linkup-cloudsql -n linkup \
     iam.gke.io/gcp-service-account=linkup-gke-cloudsql@YOUR_PROJECT.iam.gserviceaccount.com
   ```

3. Secrets (same keys as [k8s/README.md](../../README.md)), with these adjustments:
   - **`linkup-backend-secret` / `DATABASE_URL`**: async URL pointing at **`127.0.0.1:5432`** (in-pod proxy), e.g. `postgresql+asyncpg://USER:PASS@127.0.0.1:5432/linkup_app`.
   - **`REDIS_URL`** (backend secret + chat-ws secret): Memorystore, e.g. `redis://:PASSWORD@REDIS_HOST:6379/0` (API) and `/1` for chat-ws.
   - **`linkup-chat-ws-secret`**: must include **`REDIS_URL`** and **`JWT_SECRET`** (same value as backend `SECRET_KEY`) — see [chat-ws/internal/config/config.go](../../../chat-ws/internal/config/config.go).
   - **`linkup-redis-secret`**: backend Deployment still references it for `REDIS_PASSWORD`; for Memorystore-only, either create this secret with the same password embedded in `REDIS_URL`, or patch the Deployment in a forked overlay to drop that env.
4. **`EMAIL_RENDERER_URL`**: base ConfigMap uses `http://linkup-email-renderer:3001` — matches Service `linkup-email-renderer`; keep aligned if you rename Services.

## Configure Cloud SQL instance connection name

Edit **`INSTANCE_CONNECTION_NAME`** in [kustomization.yaml](./kustomization.yaml) under `configMapGenerator` → `literals` (format `project:region:instance`). Kustomize **replacements** inject it into all Auth Proxy sidecars.

Optional proxy flags (private IP, etc.): extend the `args` lists in `patches/backend-cloud-sql-proxy.yaml`, `worker-cloud-sql-proxy.yaml`, and `patches/migrate-job-proxy-json.yaml`.

## Build / apply

Kustomize must load parent paths:

```bash
kubectl kustomize k8s/overlays/gke-prod --load-restrictor LoadRestrictionsNone | kubectl apply -f -
```

Or:

```bash
kubectl apply -k k8s/overlays/gke-prod --load-kustomize-options=LoadRestrictionsNone
```

(Flag availability depends on `kubectl` version; the long `kustomize | kubectl apply -f -` form is the most portable.)

## Backend Docker image

The **`production`** target in [backend/Dockerfile](../../../backend/Dockerfile) already exists (Gunicorn + Uvicorn workers). CI should build with `--target production` — no extra Dockerfile phase is required.

## Horizontal Pod Autoscaler

Not included in this overlay by default; add HPA manifests under this folder and list them in `kustomization.yaml` when the cluster has metrics available.

## GitHub Actions (GKE)

There is **no** `deploy-gke.yml` in this repository today (**removed** intentionally — see **`docs/FUTURE_WORK.md`**); production rollout from CI targets **EC2 + Compose** (`backend-ci.yml`). To deploy these manifests from automation, **add your own workflow** (or reuse patterns from **`backend-ci`**) pushing images to Artifact Registry/GHCR and `kubectl apply`/GitOps against your cluster. Typical inputs: **`--target production`** on the backend image; patch `image:` in this overlay or use a Kustomize `images:` transformer; GCP **Workload Identity** secrets where applicable.
