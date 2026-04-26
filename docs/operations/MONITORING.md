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
