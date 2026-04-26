# Future Work

## Near-Term, High-Value (Implement Next)

### 1) Load Shedding at nginx (Fast, Concrete)

- **Decision:** Prioritize nginx-level load shedding next.
- **Scope:** Add `limit_req_zone` + `limit_req` and `limit_conn_zone` + `limit_conn` in `nginx.conf`.
- **Why now:**
  - Small implementation effort (roughly one focused workday).
  - Clear operational value: protects backend during bursts.
  - Strong interview narrative: \"how we protect the server under overload\".

### 2) Formal SLO Alerting (Prometheus Rules)

- **Decision:** Prioritize formal alert rules next.
- **Scope:** Add `monitoring/prometheus/alerts.yml` with SLO/error-budget style alerts (including burn-rate style signals).
- **Why now:**
  - Prometheus + metrics are already in place.
  - Small change with high leverage for ops maturity.
  - Strong interview narrative: \"defined SLOs with error-budget burn alerts\".

## Cache Stampede Protection: Early Refresh (Deferred)

- **Decision:** Do not implement probabilistic early refresh (XFetch-style, beta-based) at this stage.
- **Current phase:** Phase 1 mutex-based stampede protection is already implemented and is sufficient for the current scale.
- **Why deferred:**
  - Early refresh adds operational and code complexity.
  - Correct tuning requires real production traffic patterns.
  - `compute_time` distribution and `beta` calibration should be data-driven, not guessed.
- **When to revisit:**
  - After collecting enough Phase 1 metrics (lock acquisition, stampede avoided, fail-open behavior, and miss/hit trends).
  - If metrics show contention patterns that mutex alone does not handle efficiently.

This follows a senior engineering principle: avoid premature optimization, but explicitly document deferred architecture decisions so future contributors understand the rationale and rollout path.

## CQRS-Light Next Step: Materialized Views + Real Read Replica (Deferred)

- **Decision:** Keep current CQRS-light read paths, without PostgreSQL materialized views and without a dedicated read replica for now.
- **Current state:** Read models/aggregated endpoints exist, but there is no real replica topology and no materialized view refresh pipeline.
- **Why deferred:**
  - These optimizations only pay off after sustained real-world read pressure is observed.
  - Materialized views add refresh/invalidation complexity and operational ownership.
  - Read replicas add replication lag trade-offs and routing complexity.
- **When to revisit:**
  - After production traffic shows recurring read hotspots that cannot be solved with query/index tuning alone.
  - When SLOs show read latency saturation on primary under realistic load.

## API Gateway Load Shedding (nginx) (Deferred)

- **Decision:** Do not add gateway-level load shedding/concurrency limiting in nginx yet.
- **Current state:** nginx does not enforce explicit API concurrency/queue limits.
- **Why deferred:**
  - Aggressive shedding without traffic baselines can cause avoidable user-facing 503s.
  - Correct thresholds require production concurrency and latency distributions.
  - Existing app-level protections (rate limiting, async workers, retries) cover current scale.
- **When to revisit:**
  - After observing overload signatures (worker saturation, tail-latency spikes, queue buildup) under real traffic.
  - When gateway-level protection is needed to preserve core endpoints during bursts/incidents.

## CDN for Frontend Bundle (Deferred)

- **Decision:** Keep frontend bundle delivery directly via nginx for now.
- **Current state:** CloudFront is used for media delivery, not for frontend static bundle assets.
- **Why deferred:**
  - CDN for bundle adds cache invalidation/versioning workflows and deployment coupling.
  - Benefit depends on geographic traffic distribution and real cache hit potential.
  - Current traffic profile does not yet justify the extra operational layer.
- **When to revisit:**
  - After traffic and Core Web Vitals indicate clear static-asset latency bottlenecks.
  - When global distribution requirements justify edge caching for JS/CSS bundles.

## Alertmanager and Alert Tuning (Deferred)

- **Decision:** Do not finalize Alertmanager routing/escalation rules at this stage.
- **Current state:** Metrics and dashboards exist, but production-grade alert thresholds/routing are not fully tuned.
- **Why deferred:**
  - Reliable alert thresholds require real production traffic behavior (normal vs incident baselines).
  - Premature alerts create noise/fatigue and reduce operational trust.
  - Escalation policy should be calibrated to real incident patterns and on-call capacity.
- **When to revisit:**
  - After collecting enough traffic and SLO/error-budget history to define actionable alerts.
  - When alert precision/recall can be validated against real incidents.

## Multi-Tier Rate Limiting (Deferred)

- **Decision:** Do not add extra rate-limiting layers now.
- **Current state:** Token Bucket split by threat model is already implemented and sufficient at current scale.
- **Why deferred:**
  - Additional tiers now would be over-engineering.
  - More layers increase complexity (debuggability, false positives, policy drift).
  - Current posture already provides practical protection for known workloads.
- **When to revisit:**
  - If traffic patterns show clear abuse vectors not covered by current controls.
  - If incident data indicates need for layered gateway/app/user-tier policies.
