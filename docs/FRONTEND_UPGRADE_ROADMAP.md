# Frontend Upgrade Roadmap (Remaining Work Only)

This file is the single source of truth for **what is still left** to implement in frontend upgrades.

The original plan files under `.cursor/plans/` remain unchanged for deep reference.

## Current Snapshot

- Done so far: ~30%
- Remaining: ~70%
- Estimated remaining effort: ~95-100 hours
- Estimated remaining PRs: ~38

## Coverage Note (Important)

This document was initially written in a condensed format, so it grouped multiple source todos into single bullets.
To avoid missing anything, the section below includes an exhaustive checklist mapped to the original todo IDs from all 3 source plans.

## Open Prerequisites (Must Be Closed Early)

1. Add `SENTRY_AUTH_TOKEN` to GitHub Secrets for sourcemap upload flow (Tier-2 S.1 finish).
2. Run `orval + FastAPI` smoke test against `/openapi.json` before Tier-1 Stage A implementation.
3. Run post-deploy verification for HTTP/2 + WebSocket stability in production.

---

## Exhaustive Remaining Checklist (Mapped to Original Plans)

Legend:
- `[ ]` still remaining
- `[~]` likely in-progress/partially done in working tree, but requires explicit verification before marking done

### A) RQ Migration (`rq_migration_hardened_2781db04.plan.md`)

- `[~]` `stage-1-types` - complete pre-migration response typing pass in `api/*`
- `[~]` `stage-1-adr` - append RQ ADR updates in `docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`
- `[~]` `stage-3a-auth` - finish full auth query ownership and logout/query clear semantics
- `[ ]` `stage-3b-groups` - full groups queries/mutations migration + `GroupContext` slimming
- `[~]` `stage-3b-rides` - complete rides migration and WS invalidation alignment
- `[~]` `stage-3b-bookings` - complete bookings summaries/manifest/mutations + event rewiring
- `[~]` `stage-3b-passengers` - passenger requests/search/infinite/mutations + idempotency preservation
- `[ ]` `stage-3b-uploads` - presigned upload flow migration + readiness polling query
- `[~]` `stage-3b-createride` - migrate `useCreateRide` operation-token workflow to RQ mutations/signal
- `[ ]` `stage-3c-admin` - rebuild admin API usage to RQ across all admin pages; remove `useAdminFetch`
- `[~]` `stage-3d-chat` - standalone high-risk chat migration (infinite + optimistic + WS cache sync)
- `[ ]` `stage-4-msw` - MSW server/handlers/rqRender + test setup integration
- `[ ]` `stage-4-tests` - migrate targeted `useAISearch.test.ts` to MSW
- `[ ]` `stage-5-cleanup` - dead-guard cleanup + docs/FUTURE_WORK + lint sweep
- `[ ]` `verify` - per-PR verification gates (`build`, `test`, devtools/prod behavior, Sentry noise)

Notes:
- `stage-1-deps`, `stage-1-client`, `stage-1-queryclient`, `stage-1-keys`, `stage-1-provider`, `stage-2-billing`, `stage-3a-geo`, `stage-3a-notifications` appear implemented in current working tree.

### B) Tier-1 Senior FE (`frontend_senior_architecture_tier_1_05d98f56.plan.md`)

- `[ ]` `tier1-a-codegen` - orval types+axios generation flow + CI regen gate
- `[ ]` `tier1-b-bundle` - visualizer + size-limit + manualChunks + phase budget gating
- `[ ]` `tier1-c-a11y-setup` - install/configure `jsx-a11y`, `axe`, Lighthouse CI baseline
- `[ ]` `tier1-c-a11y-auth` - auth pages remediation
- `[ ]` `tier1-c-a11y-rides` - rides pages remediation
- `[ ]` `tier1-c-a11y-bookings` - bookings page remediation
- `[ ]` `tier1-c-a11y-groups` - groups pages remediation
- `[ ]` `tier1-c-a11y-chat` - messages/chat remediation
- `[ ]` `tier1-d-rum` - web vitals + extended Sentry RUM + dashboard + budget guardrails
- `[ ]` `tier1-e-form-login`
- `[ ]` `tier1-e-form-register`
- `[ ]` `tier1-e-form-verify`
- `[~]` `tier1-e-form-creategroup` - implemented via `useCreateGroup` RHF+Zod migration with full `CreateGroup.tsx` contract compatibility.
- `[~]` `tier1-e-form-createride` - deferred by architecture decision (wizard/state-machine complexity; risk > ROI at current scale).
- `[~]` `tier1-e-form-searchrides` - intentionally no-op by architecture decision (`SearchRidesForm` is props-driven/presentational; RHF adds no practical value).
- `[ ]` `tier1-e-form-messagethread`
- `[ ]` `tier1-e-form-chatpopup`
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

- `[~]` `tier2-s1-csp` - finish S.1 tail work (Sentry token wiring, sourcemap hidden/upload pipeline, post-deploy smoke)
- `[ ]` `tier2-s2-dependabot`
- `[ ]` `tier2-s2-sbom`
- `[ ]` `tier2-s3-xss`
- `[ ]` `tier2-s4-be-version`
- `[ ]` `tier2-s4-fe-version`
- `[ ]` `tier2-s5-waterfall-audit`
- `[ ]` `tier2-s6-throttle`
- `[ ]` `tier2-s7-assets`
- `[ ]` `tier2-s8-runbook`
- `[ ]` `tier2-docs`

### Remaining Count (Detailed)

- RQ detailed remaining: **15 items** (plus partial completion validation)
- Tier-1 detailed remaining: **22 items**
- Tier-2 detailed remaining: **11 items**
- Total detailed remaining backlog: **48 checklist items**

This is why the first version looked short: it grouped these into macro milestones.

---

## 1) RQ Migration - Remaining

### Stage 3a (complete remaining parts)
- [ ] Finish Auth migration: move Login/Register flow completely from manual fetch/context handling to RQ ownership.

### Stage 3b (domain migrations still missing)
- [ ] Groups full migration: `useMyGroups`, invite/members/rides queries, group mutations, and slim `GroupContext`.
- [ ] Bookings full migration: `useDriverSummary`, `usePassengerSummary`, `useRideManifest`, approve/reject/cancel mutations.
- [ ] Passengers migration: `useMyPassengerRequests`, `useRideSearch` (infinite), `useParseRideSearchWithAI`, `useRequestRideFromSearch` with `Idempotency-Key` preservation.
- [ ] Upload workflows migration: presigned upload URL + confirm flows (avatar/group image), and readiness polling via RQ.
- [ ] `CreateRide` migration: replace `useOperationToken` pattern with RQ mutation + `signal`, migrate preview/create/parse/geocode calls.

### Stage 3c
- [ ] Admin domain rebuild: replace all `features/admin/api/*` fetch paths with RQ hooks across admin pages.
- [ ] Remove legacy admin fetch abstraction after migration.

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

Remaining under `stage-3d-chat`:
- shared popup/thread cache model
- infinite messages flow + bounded pages
- optimistic message send cache patching
- WS event-to-cache synchronization strategy

Additional progress (recently completed outside full-chat scope):
- `useSearchRides` network edges migrated to React Query mutations (`search`, `load more`, `save alert`) while preserving AI/wizard/token-race behavior.
- `useMyRequests` migrated to React Query (`qk.passengers.requests` + cancel/expire cache updates).
- `AuthContext` initial mount effect dead-check fixed (cancellable async bootstrap pattern).

### Stage 4-5
- [ ] MSW test setup + migrate the targeted test file.
- [ ] Cleanup pass: remove dead guards, finalize docs/ADR updates, and deferred-items documentation.

---

## 2) Tier-1 Senior FE Architecture - Remaining

### Stage A - OpenAPI Codegen
- [ ] Configure and adopt `orval` (types + typed axios client only; no generated RQ hooks).
- [ ] Add codegen CI consistency check.

### Stage B - Bundle Budget + Visualizer
- [ ] Add bundle visualizer + `size-limit` gates.
- [ ] Apply Phase-1 budget target: main bundle <= 400KB (after Tier-2 S.7 work lands).

### Stage C - Accessibility
- [ ] Add `jsx-a11y` and runtime `axe` checks.
- [ ] Execute domain-level a11y remediation PRs.

### Stage D - Web Vitals + Sentry RUM
- [ ] Extend existing Sentry setup with tracing/replay + web vitals wiring.
- [ ] Apply cost guardrails and dashboard verification.

### Stage E - Forms Migration
- [~] Migrate 9 form surfaces to `react-hook-form + zod`.
- Current status update:
  - E.4 CreateGroup: completed.
  - E.5 CreateRide: deferred (documented decision).
  - E.6 SearchRidesForm: no-op (documented decision).

### Stage F - React Compiler
- [ ] Enable and rollout after RQ migration stabilizes.

---

## 3) Tier-2 Senior FE Hardening - Remaining

### S.1 Security Headers + Sourcemap Hardening (finish)
- [ ] Finalize CSP/Sentry key and complete sourcemap hardening pipeline (`hidden` sourcemaps + Sentry upload plugin).
- [ ] Execute post-deploy HTTP/2 + WS smoke test.

### S.2 Supply Chain
- [ ] Add Dependabot policy + security CI gate.
- [ ] Add SBOM generation and release artifact flow.

### S.3 XSS Hardening
- [ ] Enforce `react/no-danger:error`.
- [ ] Add sanitization wrapper with explicit allowlist.

### S.4 Optimistic Concurrency
- [ ] Backend: Versioned mixin prep (if needed) + Alembic + `If-Match` validation.
- [ ] Frontend: send `If-Match`, handle 409 conflicts, update cache/recovery UX.

### S.5 Waterfall Audit
- [ ] Add/execute waterfall checks across RQ Stage 3 sub-PRs.

### S.6 Client-side Global Throttle
- [ ] Add token-bucket request throttle + retry integration and tests.

### S.7 Asset Hardening
- [ ] Image lazy/eager strategy.
- [ ] i18n lazy loading + FOUE mitigation.
- [ ] Preconnect hints.

### S.8 Performance Runbook
- [ ] Create frontend performance runbook documentation.

---

## 4) Cross-Plan Sequencing Rules (Critical)

1. Complete RQ Stage 1 foundations before adding client throttle and advanced RUM extensions.
2. Coordinate shared-file changes (especially `CreateRide`, `client.ts`, `main.tsx`) to avoid PR collision.
3. Ship backend optimistic concurrency primitives before frontend conflict UX.
4. Execute bundle budget gates only after asset hardening baseline improvements.
5. Keep chat migration as a standalone PR due to higher behavioral risk.

---

## 5) Recommended Execution Order

1. Finish RQ Stage 3a/3b core domains (auth/groups/bookings/passengers/uploads/create-ride).
2. Complete Tier-2 S.1/S.2/S.3 quick hardening wins.
3. Execute Tier-2 S.4 backend then frontend concurrency.
4. Complete RQ Stage 3c admin.
5. Complete RQ Stage 3d chat standalone.
6. Finish RQ Stage 4/5 verification + cleanup.
7. Execute Tier-1 A/B/D.
8. Execute Tier-1 C/E.
9. Execute Tier-1 F and Tier-2 S.8.

---

## Reference Files (Unchanged)

- `.cursor/plans/rq_migration_hardened_2781db04.plan.md`
- `.cursor/plans/frontend_senior_architecture_tier_1_05d98f56.plan.md`
- `.cursor/plans/tier2_senior_fe_hardening_05d516e1.plan.md`
