# Monitoring

Production observability stack for Linkup.

## External dashboards (production)

**Sentry** (`sentry.io`) and **Better Stack** (`uptime.betterstack.com`) are **two separate products** from different vendors: Sentry covers **in-app** errors, traces, replay, and Vitals (wired via DSN/SDK); Better Stack covers **synthetic / external uptime** and **incident pages** against URLs such as public **`GET /livez`**. Do not conflate them—they solve different problems.

Human-facing consoles sit **next to** in-repo integrations (`SENTRY_DSN`, `VITE_SENTRY_DSN`, nginx CSP `report-uri` → Sentry ingest, etc.). Workspace URLs live here—update them if the org, project, or monitor set changes.

| Tool | Role | Links |
|------|------|--------|
| **Sentry** (`sentry.io`) | Errors, performance traces, session replay (frontend), Web Vitals, CSP/security reports routed to ingest | [Issues (14d)](https://itamar-abir.sentry.io/issues/?project=4511256490606592&statsPeriod=14d) |
| **Better Stack** | External uptime / synthetics against public **`GET /livez`**, alerting, incident timeline | [Monitors](https://uptime.betterstack.com/team/t520754/monitors) · [example incident](https://uptime.betterstack.com/team/t520754/incidents/959204833) |

Self-hosted **Prometheus + Grafana** (`docker compose --profile monitoring`) stays the metrics path inside the repo—see [Metrics stack](#metrics-stack) below.

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

- **Billing reconciler** (ריצה מתוזמנת ב-backend מ־**`app/core/lifespan.py`**, APScheduler; **`BILLING_RECONCILER_ENABLED`** ברירת מחדל **`true`** ב־config — כבה עם **`false`**): **`billing_reconciler_recovered_total`** מול **`billing_reconciler_errors_total`** — גידול מתמשך ב-errors או אפס recoveries לאורך זמן מרמז על תקלת Stripe, נעילות DB, או תור תשלומים תקועים.
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
- circuit breaker state visibility (informational) under `circuit_breakers` (Google Maps + `brevo_email`)

## Circuit breaker metrics (Prometheus)

Gauge semantics are consistent: **0** = closed (normal), **1** = half_open (probe), **2** = open (failing fast).

| Metric | Labels | Source module |
|--------|--------|----------------|
| `geo_circuit_breaker_state` | `name`: `google_geocoding`, `google_directions`, `google_distance_matrix` | `app/infrastructure/metrics.py` → geo singletons in `geo/circuit_breaker.py` |
| `brevo_circuit_breaker_state` | `name`: `brevo_email` | `app/infrastructure/metrics.py` → `brevo_email_cb` in `notifications/circuit_breaker.py` |

See **§20** in [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) and [`docs/architecture/NOTIFICATIONS.md`](../architecture/NOTIFICATIONS.md).

## Geocode cache & stampede (Prometheus)

מסלול **`get_coordinates`** ב־[`geocode_cache.py`](../../backend/app/infrastructure/geo/geocode_cache.py) משתמש ב־**`get_or_compute`** מ־[`cache_stampede.py`](../../backend/app/infrastructure/redis/cache_stampede.py) כדי למנוע סערה של קריאות Google על אותו מפתח cache כשמתבצעות בקשות מקבילות לפני שהערך חם.

| Metric | תיאור |
|--------|--------|
| `geo_cache_hits_total` | פגיעה בקריאת cache (מהיר לפני Google) |
| `geo_cache_misses_total` | המשך למסלול compute (כלול Mutex אם נדרש) |
| `cache_lock_acquired_total` | רכישת נעילה לחישוב (label `key_prefix`, למשל `geocode`) |
| `cache_stampede_avoided_total` | עוקב שנמנע מכפילת עבודה (poll אחרי בונה) |
| `cache_fail_open_total` | מעבר ללא mutex/coalesce בשגיאת Redis — עדיין fail-open בתור הגיאוקוד |

פירוט החלטה: [`docs/FEATURE_DECISIONS.md`](../FEATURE_DECISIONS.md#geocode-cache-stampede) · Highlights: [`docs/ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md).

## Rate limiting (Prometheus)

Lua אטומי ב־Redis — השוואה למדדי דחיה ו-eval latency:

| Metric | תיאור |
|--------|--------|
| `rate_limit_rejected_total` | בקשות שנחסמו (labels: `algorithm`, `endpoint`) |
| `rate_limit_redis_errors_total` | מצבי fail-open כשאין Redis (label `endpoint`) |
| `rate_limit_evaluation_seconds` | Histogram לזמני הרצת script (labels: `algorithm`) |

פירוט: [`docs/FEATURE_DECISIONS.md`](../FEATURE_DECISIONS.md#rate-limit-token-bucket) ו־ADR backend **§23**.

## Billing / Stripe (Prometheus)

Counters ב־`app/infrastructure/metrics.py` — שימושי ל-SLO על זרימת תשלום ועל התאמה מול Stripe אחרי אירועים חריגים:

| Metric | תיאור |
|--------|--------|
| `payments_initiated_total` | נוצרו Checkout Sessions |
| `payments_succeeded_total` | תשלומים הושלמו |
| `payments_failed_total` | תשלומים נכשלו |
| `payments_canceled_total` | בוטלו / פגו |
| `stripe_webhook_received_total` | webhook התקבל (label `event_type`) |
| `stripe_webhook_errors_total` | אימות חתימה נכשל |
| `billing_reconciler_runs_total` | ריצות reconciler |
| `billing_reconciler_recovered_total` | תשלומים שחודשו/סונכרנו מתוך stale pending |
| `billing_reconciler_errors_total` | כשלים פר־תשלום בתוך ריצת reconciler |
| `billing_idempotency_hits_total` | פגיעות במטמון אידמפוטנטיות checkout |

**הערת מקור קוד:** ב־[`app/infrastructure/metrics.py`](../../backend/app/infrastructure/metrics.py) מוגדרים גם מדדים המסומנים **DEFERRED** (עדיין ללא call sites) — למשל Gauge **`outbox_pending_depth`** ו-Counter **`geo_requests_total`** — אל תצפו לסדרות זמן “חיות” מהם עד שיופעלו בקוד.

פירוט API ו-env: [`docs/architecture/API.md`](../architecture/API.md) (Billing), [`docs/architecture/DEVELOPMENT.md`](../architecture/DEVELOPMENT.md).

## Liveness & Readiness Probes

Two probe endpoints live at FastAPI **root** (not under `/api/v1/`) on purpose: they are infra signals, decoupled from API versioning. See [`backend/app/main.py`](../../backend/app/main.py).

| Endpoint | Exposure | Payload | Intended consumers |
|---|---|---|---|
| `GET /livez` | **Public** (via nginx) | `{"status": "alive"}` | External uptime monitors (UptimeRobot / Pingdom / Datadog synthetic) |
| `GET /readyz` | **Internal only** (loopback-restricted at nginx) | DB / Redis / RabbitMQ / circuit-breaker status | Operators on the EC2 host, internal scripts; Docker Compose **`backend`** healthcheck (`http://localhost:8000/readyz` inside the container, bypassing nginx) |

### Why `/readyz` is not public

`/readyz` enumerates the internal dependency stack (Postgres, Redis, RabbitMQ, Google API circuit-breaker state). Exposing that publicly is free reconnaissance for an attacker (port-scan targets, CVE matching). The exposure policy is enforced in the rendered edge config (from [`nginx/nginx.conf.template`](../../nginx/nginx.conf.template) → `nginx/nginx.conf`; see [`scripts/ops/render-nginx-conf.sh`](../../scripts/ops/render-nginx-conf.sh) / [`docs/SECURITY_HEADERS.md`](../SECURITY_HEADERS.md)):

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

## Prometheus — רישום מטריקות (מחוברות מול שמורות)

מקור האמת לשמות והטיפוסים: [`backend/app/infrastructure/metrics.py`](../../backend/app/infrastructure/metrics.py).

הטבלאות למעלה (Billing, Rate limit, Geocode, Circuit breaker, RabbitMQ וכו’) מתארות מטריקות ש**בפועל מתעדכנות מהקוד** בזרימות הרלוונטיות.

**מוגדרים ב־`metrics.py` אך כרגע לא מוזנים מקריאות בקוד** (אל תבנו עליהם dashboards/SLO עד wiring):  
`rabbitmq_consumer_restarts_total`, `notifications_sent_total`, `notifications_failed_total`,  
`outbox_pending_depth`, `geo_requests_total`, ו־Histogram **`noop_latency_histogram`** (שמור לעתיד).

**עומק DLQ:** [`run_dlq_monitor`](../../backend/app/infrastructure/rabbitmq/dlq_monitor.py) כותב **לוגים** (warning/critical לפי סף). ה־Gauge **`rabbitmq_dlq_depth`** אינו מתעדכן מהמוניטור הנוכחי — ניטור עומק דרך לוגים / ממשק RabbitMQ, או הרחבת הקוד אם תרצו ייצוא ל־Prometheus.

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
