# Monitoring

Production observability stack for Linkup.

## Metrics Stack

- **Backend:** Prometheus endpoint at `GET /metrics`
- **Workers:** dedicated metrics ports
  - `notification-worker:9091`
  - `task-worker:9092`
  - `ai-worker:9093`
- **Prometheus + Grafana:** available via compose profile `monitoring`

## Key Signals to Track

## Availability / latency

- HTTP 2xx/4xx/5xx rate
- request latency (`p50`, `p95`, `p99`)
- in-progress request count

## Async reliability

- outbox processed vs failed
- RabbitMQ retries and DLQ depth
- consumer restart counters
- worker task failure counters

## RabbitMQ resilience (important)

- `rabbitmq_consumer_restarts_total`
- `rabbitmq_consumer_iterator_restarts_total`

Interpretation:

- occasional increments are expected during broker reconnects
- sustained growth means consumer/channel instability and should trigger investigation

## Infrastructure health

- DB, Redis, RabbitMQ health from `/api/v1/health`
- circuit breaker state visibility (informational) under `circuit_breakers`

## Liveness & Readiness Probes

Two probe endpoints live at FastAPI **root** (not under `/api/v1/`) on purpose: they are infra signals, decoupled from API versioning. See [`backend/app/main.py`](../../backend/app/main.py).

| Endpoint | Exposure | Payload | Intended consumers |
|---|---|---|---|
| `GET /livez` | **Public** (via nginx) | `{"status": "alive"}` | External uptime monitors (UptimeRobot / Pingdom / Datadog synthetic), Docker healthcheck (`localhost:8000/livez` inside container) |
| `GET /readyz` | **Internal only** (loopback-restricted at nginx) | DB / Redis / RabbitMQ / circuit-breaker status | Operators on the EC2 host, internal scripts |

### Why `/readyz` is not public

`/readyz` enumerates the internal dependency stack (Postgres, Redis, RabbitMQ, Google API circuit-breaker state). Exposing that publicly is free reconnaissance for an attacker (port-scan targets, CVE matching). The exposure policy is enforced in [`nginx/nginx.conf`](../../nginx/nginx.conf):

```nginx
location = /readyz {
  allow 127.0.0.1;
  allow ::1;
  deny all;
  proxy_pass http://backend;
  ...
}
```

`/livez` stays public because its payload is innocuous and external uptime checks need it.

### Reading `/readyz` as an operator

From the EC2 host (loopback — passes nginx allow):

```bash
curl -ks https://localhost/readyz
```

Or directly against the backend container, bypassing nginx (useful when nginx itself is the suspect):

```bash
docker exec linkup_backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/readyz').read())"
```

### Verifying the exposure policy

After any nginx config change, confirm:

```bash
# /livez — expected 200 + JSON
curl -ks -o /dev/null -w "%{http_code}\n" https://linkup.itamarabir.com/livez

# /readyz from public domain — expected 403 Forbidden
curl -ks -o /dev/null -w "%{http_code}\n" https://linkup.itamarabir.com/readyz

# /readyz from EC2 host loopback — expected 200 + JSON
curl -ks https://localhost/readyz
```

### Future work

If external readiness monitoring becomes a requirement (e.g. dependency-aware status page), the path is to add Basic-Auth or an `allow` for the monitor's static IP — *not* to drop the loopback restriction. See [`docs/FUTURE_WORK.md`](../FUTURE_WORK.md).

## Alerting Baseline

Suggested initial alerts:

- backend `5xx` rate above threshold for 5 minutes
- API `p95` latency above threshold for 10 minutes
- DLQ depth above warning/critical threshold
- worker process down / restart storm
- disk usage above 85% on EC2 host

## SLO Baseline (starting point)

- API availability: `99.9%` monthly
- API latency: `p95 < 400ms`, `p99 < 900ms` on critical routes
- async success ratio (outbox + queue processing): `>= 99.5%`

When error budget burn exceeds policy threshold, prioritize reliability work over feature rollout.

## Operational References

- Deploy + rollback flow: [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)
- Incident handling: [`docs/operations/RUNBOOK.md`](RUNBOOK.md)
- Event topology and retries: [`docs/architecture/EVENTS.md`](../architecture/EVENTS.md)
