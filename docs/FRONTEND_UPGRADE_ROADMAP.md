# Frontend Upgrade Roadmap (Remaining Work Only)

This file is the single source of truth for **what is still left** to implement in frontend upgrades.

The original plan files under `.cursor/plans/` remain unchanged for deep reference.

## Current Snapshot

- Progress is tracked in the **checklists below**; headline percentages are approximate and not recomputed every merge.
- Estimated remaining effort order-of-magnitude: **tens of hours** across RQ domains, a11y remediation, compiler rollout, and verification gates.

## Coverage Note (Important)

This document was initially written in a condensed format, so it grouped multiple source todos into single bullets.
To avoid missing anything, the section below includes an exhaustive checklist mapped to the original todo IDs from all 3 source plans.

## Open Prerequisites (Must Be Closed Early)

1. `SENTRY_AUTH_TOKEN` / `SENTRY_ORG` / `SENTRY_PROJECT` are now wired for frontend sourcemap upload in `publish-image`; remaining S.1 work is post-deploy verification/tuning.
2. **OpenAPI → Orval codegen** is enforced in CI (`contract-codegen` job: `npm run gen:api` + `git diff --exit-code` on `frontend/src/api/generated/`).
3. Run post-deploy verification for **TLS edge + WebSocket** stability in production (`nginx` → backend/chat-ws; if you enable **`http2`** on `listen 443 ssl`, re-verify upgrades).

---

## Exhaustive Remaining Checklist (Mapped to Original Plans)

Legend:
- `[ ]` still remaining
- `[~]` likely in-progress/partially done in working tree, but requires explicit verification before marking done

### A) RQ Migration (`rq_migration_hardened_2781db04.plan.md`)

- `[x]` `stage-1-types` - API types driven by **`frontend/openapi-snapshot.json` → Orval → `src/api/generated/`** with CI drift gate; thin `api/*` wrappers consume generated types.
- `[x]` `stage-1-adr` - RQ infrastructure and Stage 3+ migration decisions documented (**ADR Frontend §13+**, Stage 3b §15).
- `[~]` `stage-3a-auth` - finish full auth query ownership — **logout / session-expired / bootstrap-failed teardown semantics shipped** (`tearDownSession`, `auth:session-expired`, RQ **`captureExceptionOnce`** + 401-only Sentry skip); remaining: deeper “auth query ownership” refactors if still desired per product scope
- `[ ]` `stage-3b-groups` - full groups queries/mutations migration + `GroupContext` slimming
- `[x]` `stage-3b-rides` - **`MyRides.tsx`**: `useQuery` (`qk.rides.list`), `useMutation` לביטול, invalidation מ־`useUserEvent` + `useRideWebSocket`.
- `[x]` `stage-3b-bookings` - **`useMyBookingsDriver`** / **`useMyBookingsPassenger`**: `useQuery` לסיכומים, `useMutation` לאשר/לדחות/לבטל + אירועי WS/user-event.
- `[x]` `stage-3b-passengers` - **`useMyRequests`** + **`useSearchRides`** (mutations לחיפוש/load-more/alert) + **`useJoinRide`** עם Idempotency-Key כמתועד ב־Highlights.
- `[ ]` `stage-3b-uploads` - presigned upload flow migration + readiness polling query
- `[~]` `stage-3b-createride` - migrate `useCreateRide` operation-token workflow to RQ mutations/signal
- `[~]` `stage-3d-chat` - standalone high-risk chat migration: **optimistic outbound send + `ChatListRow` + WS/REST reconciliation shipped** (`types/chatList`, `applyInboundRealMessage`); **WS reconnect hardening shipped** (`reconnectBackoff.ts` → `useChatWebSocket` / `useReconnectingWebSocket` / `useReconnectingWebSocketState`); **remaining**: React Query for thread/popup/infinite scroll + broader “WS cache sync” if still desired
- `[ ]` `stage-4-msw` - MSW server/handlers/rqRender + test setup integration
- `[ ]` `stage-4-tests` - migrate targeted `useAISearch.test.ts` to MSW
- `[ ]` `stage-5-cleanup` - dead-guard cleanup + docs/FUTURE_WORK + lint sweep
- `[ ]` `verify` - per-PR verification gates (`build`, `test`, devtools/prod behavior, Sentry noise)

Notes:
- `stage-1-deps`, `stage-1-client`, `stage-1-queryclient`, `stage-1-keys`, `stage-1-provider`, `stage-2-billing`, `stage-3a-geo`, `stage-3a-notifications` appear implemented in current working tree.
- `stage-3b-rides`, `stage-3b-bookings`, `stage-3b-passengers` marked **`[x]`** above (verified in `MyRides.tsx`, `MyBookings/*`, `useMyRequests`, `useSearchRides`).

### B) Tier-1 Senior FE (`frontend_senior_architecture_tier_1_05d98f56.plan.md`)

- `[~]` `tier1-c-a11y-setup` - **`eslint-plugin-jsx-a11y`** (recommended preset + progressive warn rules) and **dev-only `@axe-core/react`** are wired; **Lighthouse CI baseline** still open.
- `[ ]` `tier1-c-a11y-auth` - auth pages remediation
- `[ ]` `tier1-c-a11y-rides` - rides pages remediation
- `[ ]` `tier1-c-a11y-bookings` - bookings page remediation
- `[ ]` `tier1-c-a11y-groups` - groups pages remediation
- `[ ]` `tier1-c-a11y-chat` - messages/chat remediation
- `[~]` `tier1-d-rum` - **Prod `Sentry.init`**: Browser Tracing + Replay + **web-vitals → Sentry metrics** (`main.tsx`); remaining: **cost/dashboard guardrails** and formal threshold policy (**`docs/FUTURE_WORK.md`** — Web Vitals Thresholds).
- `[~]` `tier1-e-form-creategroup` - implemented via `useCreateGroup` RHF+Zod migration with full `CreateGroup.tsx` contract compatibility.
- `[~]` `tier1-e-form-createride` - deferred by architecture decision (wizard/state-machine complexity; risk > ROI at current scale).
- `[~]` `tier1-e-form-searchrides` - intentionally no-op by architecture decision (`SearchRidesForm` is props-driven/presentational; RHF adds no practical value).
- `[~]` `tier1-e-form-messagethread` - **לא בתור משימת RHF פעילה** — Composer חד־שדותי + WS; החלטה ב־**`docs/FUTURE_WORK.md`** (E.7).
- `[~]` `tier1-e-form-chatpopup` - כנ"ל (**E.8** ב־**`docs/FUTURE_WORK.md`**).
- `[ ]` `tier1-f-compiler-setup`
- `[ ]` `tier1-f-compiler-presentational`
- `[ ]` `tier1-f-compiler-rq-hooks`
- `[ ]` `tier1-f-compiler-pages`
- `[ ]` `tier1-f-compiler-cleanup`

Notes:
- Tier-1 dependency groundwork (`react-hook-form`, `zod`, `@hookform/resolvers`) exists.
- Stage E decisions updated:
  - E.4 (`CreateGroup`) shipped.
  - E.5 (`CreateRide`) deferred and documented in `docs/FUTURE_WORK.md`.
  - E.6 (`SearchRidesForm`) kept as-is by design (presentational, controlled via hook props).

### C) Tier-2 Hardening (`tier2_senior_fe_hardening_05d516e1.plan.md`)

- `[~]` `tier2-s1-csp` - finish S.1 tail work (post-deploy smoke + sourcemap verification/tuning)
- `[ ]` `tier2-s2-sbom`
- `[ ]` `tier2-s4-be-version`
- `[ ]` `tier2-s4-fe-version`
- `[ ]` `tier2-s5-waterfall-audit`
- `[~]` `tier2-s7-assets` - baseline S.7 בפרודקשן (ראו סעיף **S.7** למטה); נשארו שערים/קריטריונים למדידה.
- `[ ]` `tier2-docs`

### Remaining Count (Detailed)

- Treat the **per-line legend** (`[ ]` / `[~]` / `[x]`) as source of truth; macro counts go stale quickly.
- Several Tier-1 / Tier-2 items were **`[x]` completed** inline above (stage-1 types/ADR; Tier-2 XSS/throttle/runbook/etc. as marked).

This is why the first version looked short: it grouped these into macro milestones.

---

## 1) RQ Migration - Remaining

### Stage 3a (complete remaining parts)
- [ ] Finish Auth migration: move Login/Register flow completely from manual fetch/context handling to RQ ownership.

### Stage 3b (domain migrations still missing)
- [ ] Groups full migration: רשימת קבוצות ב־`GroupContext` כבר `useQuery`; **`useGroupManageLists`** עדיין `useEffect` + `useState` ל־members/rides — להעביר ל־RQ + מוטציות הזמנה/הרשאות לפי הצורך; לרזות `GroupContext` אם עדיין רלוונטי.
- [x] Bookings full migration — **בוצע** (`useMyBookingsDriver` / `useMyBookingsPassenger`).
- [x] Passengers migration (בקשות + חיפוש + join עם Idempotency-Key) — **בוצע** (`useMyRequests`, `useSearchRides`, `useJoinRide`).
- [x] Rides list (My Rides) — **בוצע** (`MyRides.tsx`).
- [ ] Upload workflows migration: presigned upload URL + confirm flows (avatar/group image), and readiness polling via RQ (כיום polling ידני ב־`useProfile` / זרימות דומות).
- [ ] `CreateRide` migration: replace `useOperationToken` pattern with RQ mutation + `signal`, migrate preview/create/parse/geocode calls.

### Stage 3c
- Completed and removed from remaining scope (`stage-3c-admin`).

### Stage 3d (high risk, standalone PR)
- [~] Chat domain unified migration:
  - shared cache for popup + thread
  - infinite messages with `maxPages: 20`
  - `refetchOnReconnect: false` where WS is source-of-truth
  - optimistic send with `InfiniteData` patching
  - WS event handling via `queryClient` cache APIs

Safe subset shipped (completed):
- `useChatUnreadMessages` moved from manual `setInterval` to `useQuery` polling (`qk.chat.unread`) with invalidate-based refresh API.
- `useChatNotificationsFeed` moved from manual `setInterval` to `useQuery` polling (`qk.notifications.all`) with invalidate-based refresh API and preserved reducer contracts.
- `Messages.tsx` moved from manual `useState/useEffect` fetch lifecycle to `useQuery` (`qk.chat.conversations`) with preserved sort/render semantics.
- **WebSocket reconnect hardening:** **`computeReconnectDelayMs`** ([`frontend/src/utils/reconnectBackoff.ts`](../frontend/src/utils/reconnectBackoff.ts)) wired into **`useChatWebSocket`**, **`useReconnectingWebSocket`**, **`useReconnectingWebSocketState`** — base **3s**, cap **30s**, **±20%** jitter; documented in [`docs/architecture/REALTIME.md`](architecture/REALTIME.md), [`docs/FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff).

Remaining under `stage-3d-chat`:
- shared popup/thread cache model
- infinite messages flow + bounded pages
- optimistic message send cache patching
- WS event-to-cache synchronization strategy

Additional progress (recently completed outside full-chat scope):
- Chat **outbound REST**: stable **Idempotency-Key** lifecycle in `useMessageThread` / `useChatPopup` (shared helpers in `utils/outboundIdempotencyKey.ts`), **`appendMessageDedupById`** for list updates + WebSocket path (`utils/chatMessagesMerge.ts`), **`isChatIdempotencyKeyMismatch` on 422** (`utils/apiError.ts`); documented in `docs/ENGINEERING_HIGHLIGHTS.md`, `docs/architecture/API.md`, ADR Frontend §2 / Backend §25.
- `useSearchRides` network edges migrated to React Query mutations (`search`, `load more`, `save alert`) while preserving AI/wizard/token-race behavior.
- `useMyRequests` migrated to React Query (`qk.passengers.requests` + cancel/expire cache updates).
- `AuthContext` initial mount effect dead-check fixed (cancellable async bootstrap pattern).

### Stage 4-5
- [ ] MSW test setup + migrate the targeted test file.
- [ ] Cleanup pass: remove dead guards, finalize docs/ADR updates, and deferred-items documentation.

---

## 2) Tier-1 Senior FE Architecture - Remaining

### Stage A - OpenAPI Codegen
- Completed and removed from remaining scope (`tier1-a-codegen`).

### Stage B - Bundle Budget + Visualizer
- Completed and removed from remaining scope (`tier1-b-bundle`).
- [ ] Apply Phase-1 budget target: main bundle <= 400KB (after Tier-2 S.7 work lands).

### Stage C - Accessibility
- [x] Add `jsx-a11y` (ESLint flat config) and **dev-only** runtime `axe` checks (`main.tsx`).
- [ ] Lighthouse CI baseline (optional) and domain-level a11y remediation PRs (auth/rides/bookings/groups/chat).

### Stage D - Web Vitals + Sentry RUM
- [x] Extend Sentry with **tracing + replay + web-vitals metrics** in production (`main.tsx`).
- [ ] Cost guardrails, dashboard verification, and threshold enforcement policy (**`docs/FUTURE_WORK.md`**).

### Stage E - Forms Migration
- [~] רכיבי טפסים שנשארו ב־**RHF+zod** רלוונטיים: לא נשארו מסכים מרכזיים פתוחים; **E.5/E.6/E.7/E.8** מוגדרים כ־defer/no-op ב־**`docs/FUTURE_WORK.md`**.
- Current status update:
  - E.1 Login: completed.
  - E.2 Register: completed.
  - E.3 VerifyEmail: completed.
  - E.4 CreateGroup: completed.
  - E.5 CreateRide: deferred (documented decision).
  - E.6 SearchRidesForm: no-op (documented decision).
  - E.7 / E.8 MessageThread / ChatPopup: no-op (documented decision).

### Stage F - React Compiler
- [ ] Enable and rollout after RQ migration stabilizes.

---

## 3) Tier-2 Senior FE Hardening - Remaining

### S.1 Security Headers + Sourcemap Hardening (finish)
- [x] CSP: enforcing **`Content-Security-Policy`** on Compose edge nginx (**`nginx/nginx.conf.template`** → `nginx/nginx.conf` via **`scripts/ops/render-nginx-conf.sh`** / CI; **`SENTRY_REPORT_URI`** in **`backend/.env`**); **`script-src`** hardened (**ללא** `'unsafe-inline'`) עם bootstrap ב־**`frontend/public/bootstrap.js`**; `frame-src` + Google Sign-In; `report-uri` from env — **`docs/SECURITY_HEADERS.md`** / **`docs/ENGINEERING_HIGHLIGHTS.md`**.
- [~] Post-deploy verification: smoke login/chat/maps/uploads/billing; watch Sentry CSP reports; tune allowlists if needed (**K8s:** keep **`k8s/frontend/nginx-configmap.yaml`** in sync when using that ingress path).
- [ ] Execute post-deploy edge (TLS/nginx) + WebSocket smoke test (disciplined checklist; include HTTP/2 only if enabled in **`nginx/nginx.conf.template`**).

### S.2 Supply Chain
- [ ] SBOM generation/release artifact flow deferred to `docs/FUTURE_WORK.md`.

### S.3 XSS Hardening
- Completed and removed from remaining scope (`tier2-s3-xss`).

### S.5 Waterfall Audit
- [ ] Add/execute waterfall checks across RQ Stage 3 sub-PRs.

### S.6 Client-side Global Throttle
- Completed and removed from remaining scope (`tier2-s6-throttle`).

### S.7 Asset Hardening
- [x] Baseline shipped (**S.7**): targeted image `loading`/`fetchpriority`, hybrid i18n (`i18next-http-backend` + critical namespace preload), `index.html` preconnect/dns-prefetch — see **`docs/ENGINEERING_HIGHLIGHTS.md`**.
- [ ] Formal regression gates / measurable acceptance criteria for asset + i18n behavior (per audit matrix §6.9).

### S.8 Performance Runbook
- Completed and removed from remaining scope (`tier2-s8-runbook`).

---

## 4) Cross-Plan Sequencing Rules (Critical)

1. **Stage 1 foundations** (`stage-1-types`, `stage-1-adr`) are **closed** — still sequence risky refactors (`CreateRide`, chat) carefully against client throttle and RUM guardrails work.
2. Coordinate shared-file changes (especially `CreateRide`, `client.ts`, `main.tsx`) to avoid PR collision.
3. Ship backend optimistic concurrency primitives before frontend conflict UX.
   - Note: OCC scope deferred to `docs/FUTURE_WORK.md` for current planning window.
4. Execute bundle budget gates only after asset hardening baseline improvements.
5. Keep chat migration as a standalone PR due to higher behavioral risk.

---

## 5) Recommended Execution Order

1. Finish RQ Stage 3a/3b remaining scope (**auth**, **groups manage** + העלאות + **CreateRide**; rides/bookings/passengers לרשימות הראשיות כבר ב־RQ).
2. Complete Tier-2 S.1/S.2 quick hardening (**S.3 XSS** baseline already shipped — see Tier-2 section).
3. Execute Tier-2 S.4 backend then frontend concurrency.
4. **RQ Stage 3c admin** is complete — keep guarding regressions in future PRs.
5. Complete RQ Stage 3d chat standalone.
6. Finish RQ Stage 4/5 verification + cleanup.
7. Tier-1 **A (codegen)** and **B (bundle tooling)** are shipped; prioritize **D** guardrails, then **C/E/F**.
8. Execute Tier-1 C/E remediation (a11y + forms backlog).
9. Execute Tier-1 F; Tier-2 **S.8 runbook** is marked complete — revisit only if perf posture changes materially.

---

## 6) Implementation Audit Matrix (Cloud-Ready Status)

Use this section as the authoritative status when sharing to cloud/remote reviewers.

Status keys:
- `Implemented in code`: `Yes` / `No` / `Partial`
- `Completion`: `FULL` / `PARTIAL` / `NOT IMPLEMENTED`
- `Missing for FULL`: exact remaining work

### 6.3 `tier1-c-a11y-setup` + remediation

- Implemented in code: `Partial`
- Completion: `PARTIAL`
- Evidence:
  - `frontend/eslint.config.js` (`eslint-plugin-jsx-a11y`)
  - `frontend/src/main.tsx` (`@axe-core/react` in dev)
- Missing for FULL:
  - Close remediation across targeted domains (auth/rides/bookings/groups/chat).
  - Lighthouse CI baseline (still open) plus stable CI-level accessibility verification beyond local/dev checks.

### 6.4 `tier1-d-rum` (Web Vitals + Sentry RUM)

- Implemented in code: `Yes`
- Completion: `PARTIAL`
- Evidence:
  - `frontend/src/main.tsx` (`Sentry.browserTracingIntegration`, `replayIntegration`, dynamic `web-vitals` → Sentry distributions)
- Missing for FULL:
  - Cost/dashboard guardrails and release-level threshold enforcement (**`docs/FUTURE_WORK.md`** — Web Vitals Thresholds).

### 6.9 `tier2-s7-assets`

- Implemented in code: `Yes`
- Completion: `PARTIAL` (baseline shipped; gates still open)
- Evidence:
  - `frontend/index.html` (`preconnect`/`dns-prefetch`)
  - `frontend/src/i18n/config.ts` (`i18next-http-backend`)
  - route/image lazy loading + `loading`/`fetchpriority` tuning (see **S.7** in `docs/ENGINEERING_HIGHLIGHTS.md`)
- Missing for FULL:
  - Add measurable acceptance criteria + CI/manual verification gates to prevent regressions.

### 6.11 `stage-3b` (RQ domain migration)

- Implemented in code: `Partial`
- Completion: `PARTIAL`
- Evidence:
  - **`MyRides`**, **`MyBookings`** (נהג/נוסע), **`useMyRequests`**, **`useSearchRides`**, **`GroupContext`** list — RQ כמתועד בקוד; ניהול קבוצה (members/rides ב־`useGroupManageLists`) עדיין fetch ידני.
- Missing for FULL:
  - הגירת **GroupManage** lists + מוטציות קשורות ל־RQ; **Upload** (polling readiness) תחת RQ; **CreateRide** (מכונת מצבים) לפי יעדי השלב.

### 6.12 `stage-3c` (Admin migration)

- Implemented in code: `Yes`
- Completion: `FULL`
- Evidence:
  - Most admin hooks are RQ-based
  - legacy `useAdminFetch.ts` path removed
  - `AdminLookup.tsx` now uses `useMutation` for on-demand ride/booking lookup instead of manual async state
- Missing for FULL:
  - None.

### 6.13 `stage-3d` (Chat migration)

- Implemented in code: `Partial`
- Completion: `PARTIAL`
- Evidence:
  - Unread/conversation subset moved to RQ
- Missing for FULL:
  - shared popup/thread cache
  - infinite messages model (bounded pages)
  - optimistic send cache patching
  - WS event-to-cache synchronization closure

---

## Reference Files (Unchanged)

- `.cursor/plans/rq_migration_hardened_2781db04.plan.md`
- `.cursor/plans/frontend_senior_architecture_tier_1_05d98f56.plan.md`
- `.cursor/plans/tier2_senior_fe_hardening_05d516e1.plan.md`
