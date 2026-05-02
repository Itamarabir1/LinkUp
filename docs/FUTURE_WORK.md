# Future Work

## GKE Migration Path (Deferred)

- **Decision:** Keep Kubernetes manifests in `k8s/`, but remove `.github/workflows/deploy-gke.yml` for now.
- **Current state:** Production deploy path is EC2 + Docker Compose, and GCP secrets/vars are not configured in GitHub Actions.
- **Why now:**
  - Prevent noisy CI/workflow validation failures from an inactive deployment path.
  - Preserve migration-ready assets (`k8s/`) without pretending the pipeline is operational.
  - Keep the repository aligned with the currently supported production topology.
- **When to revisit:**
  - After deciding to migrate runtime to GKE and provisioning required GCP credentials/secrets.
  - When CI ownership includes a tested GKE rollout + rollback path.

## Near-Term, High-Value (Implement Next)

_Nginx connection/request rate limiting (`limit_req` / `limit_conn`) is intentionally **not** scheduled here — it is covered under [API Gateway Load Shedding (Deferred)](#api-gateway-load-shedding-nginx-deferred) until traffic baselines justify thresholds._

### 1) Formal SLO Alerting (Prometheus Rules)

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

## Chat Full React Query Migration (Deferred)

- **Decision:** Defer full chat-domain migration (`useConversationMessages` + `useChatPopup` + WS write path integration) for now.
- **Current state:** Chat is WS-driven and stable in production.
- **Why deferred:**
  - Migration risk is currently higher than practical benefit at the current scale.
  - Reconnect backfill is hardened: every chat WS **`onOpen`** runs REST gap fill (**`after=`** + **`before=next_cursor`** במחזור עד **`has_more`** או מכסת לקוח) with **`lastMessageIdRef ?? 0`** and a fixed **`lastMessageIdRef`** sync (see **`ENGINEERING_HIGHLIGHTS.md`** + **[`FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md#chat-thread-reconnect)** + **`fetchMissedGap.ts`**); message-stream UX remains WS-first.
  - A full shift to shared cache + infinite query + optimistic flow would increase blast radius in a high-risk domain.
- **Safe subset already shipped** (polling/unread + שיחות + התראות; פער reconnect; אופטימי outbound — לא מיגרציית צ'אט מלאה ל־RQ cache): **`docs/ENGINEERING_HIGHLIGHTS.md`**, **`docs/FEATURE_DECISIONS.md`** (chat-thread-reconnect).
- **When to revisit:**
  - If measurable UX issues appear (popup/thread desync, duplicate/missing messages, unread drift), or
  - If traffic/complexity justifies a dedicated, isolated chat migration program.

## S.4 — Optimistic Concurrency Control (OCC) (Deferred)

- **Decision:** Defer OCC for user profile updates for now.
- **Current state:** `PUT /users/me` exists in backend, but frontend `Profile.tsx` is currently read-only (no profile edit form).
- **Why deferred:**
  - OCC solves real risk when concurrent multi-tab editing exists.
  - Without editable profile form in frontend, OCC adds protocol complexity without current product value.
- **When to revisit:**
  - When profile editing UI is introduced in frontend.
  - Implement as a full contract: `version` field on `User` model + `If-Match` request header + explicit `409` conflict handling path in frontend UX.

## Frontend Forms Scope: E.5/E.6 (Deferred / No-op)

- **Decision (E.6 SearchRidesForm):** no RHF migration needed right now.
- **Current state:** `SearchRidesForm` is presentational and controlled via props from `useSearchRides`; it has no local form-state ownership.
- **Why no-op now:**
  - RHF would duplicate existing control flow without reducing complexity.
  - The meaningful network/state orchestration already lives in `useSearchRides` mutations.

- **Decision (E.5 CreateRide):** defer RHF migration.
- **Current state:** `useCreateRide` is a wizard/state-machine flow (preview/create, AI parse, geolocation, operation-token race guards).
- **Why deferred:**
  - `CreateRide` is orchestration-heavy (idle/locating/previewing/creating state machine + AI flow + operation-token race protection).
  - RHF provides limited ROI in this flow and can increase complexity/risk for sequencing regressions.
- **When to revisit:**
  - If/when the wizard is simplified materially and form-state ownership becomes a clear fit for RHF+zod.

## Frontend Forms Scope: E.7/E.8 (Deferred / No-op)

- **Decision (E.7 MessageThread + E.8 ChatPopup):** defer RHF migration.
- **Current state:** message send forms are single-field textarea flows with no validation requirements.
- **Why deferred:**
  - Input state is managed in `useMessageThread` with draft saving to `localStorage`.
  - The composer path is integrated with WebSocket typing indicators and send flow.
  - RHF adds little practical value for this shape (single input, no schema validation), while increasing integration complexity with the WS layer.
- **When to revisit:**
  - If chat composer evolves into multi-field input or adds real validation/business rules where RHF+zod yields clear ROI.

## SBOM Generation + Release Artifact Flow (Deferred)

- **Decision:** Defer SBOM generation and release artifact publication for now.
- **Current state:** No dedicated SBOM generation step is enforced in CI/CD release flow.
- **Why deferred:**
  - Requires choosing a single toolchain and ownership model (generation, storage, and verification).
  - Adds release-pipeline steps that should be rolled out together with clear supply-chain policy.
  - Current priority is functional/platform hardening already in progress.
- **When to revisit:**
  - When release hardening scope includes software supply-chain controls.
  - Implement with a CI step that generates SBOM on every release build and publishes it as a versioned artifact.

## Web Vitals Thresholds Enforcement (Deferred)

- **Decision:** Defer explicit Web Vitals threshold enforcement as a formal release gate.
- **Current state:** RUM instrumentation exists, but explicit `LCP`/`INP`/`CLS` thresholds are not enforced as guardrails.
- **Why deferred:**
  - Reliable thresholds should be calibrated from real traffic baselines to avoid noisy false positives.
  - Enforcement path (CI/post-deploy + alert routing) should be introduced as one coherent policy.
  - Current observability maturity is improving, but threshold policy is not yet finalized.
- **When to revisit:**
  - After baseline vitals distributions are stable enough to define actionable thresholds.
  - Add automated regression enforcement (post-deploy check and alerting) tied to release criteria.
