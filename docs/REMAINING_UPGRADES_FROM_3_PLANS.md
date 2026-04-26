# Remaining Upgrades From 3 Plans

הקובץ הזה מרכז את **כל מה שנשאר לבצע** לפי 3 קבצי התכנון:

- `c:\Users\user\.cursor\plans\rq_migration_hardened_2781db04.plan.md`
- `c:\Users\user\.cursor\plans\frontend_senior_architecture_tier_1_05d98f56.plan.md`
- `c:\Users\user\.cursor\plans\tier2_senior_fe_hardening_05d516e1.plan.md`

> הערה: ב־3 קבצי המקור רוב ה־todos מסומנים `pending`, לכן הרשימה כאן משקפת את ה־backlog שנותר לפי התכנון עצמו.

## Snapshot

- RQ Migration: 22 items (+ 1 verify gate)
- Tier-1 Architecture: 22 items
- Tier-2 Hardening: 11 items
- **Total remaining backlog: 55 items (+ verify gate)**

---

## A) RQ Migration - Remaining

### Stage 1 - Infrastructure
- [ ] `stage-1-deps` - install RQ/MSW deps
- [ ] `stage-1-types` - pre-migration response typing tightening
- [ ] `stage-1-client` - `__sentryCaptured` dedupe marker in axios interceptor
- [ ] `stage-1-queryclient` - `queryClient` defaults + retry policy + Sentry dedupe
- [ ] `stage-1-keys` - `qk` + `mk` factories for all domains
- [ ] `stage-1-provider` - mount `QueryClientProvider` + devtools guard
- [ ] `stage-1-adr` - append frontend ADR section

### Stage 2 - Billing first RQ user
- [ ] `stage-2-billing` - billing domain + premium banner + payment success/cancel flow

### Stage 3a - Low risk domains
- [ ] `stage-3a-geo` - geo migration (`mapsKey`, reverse geocode)
- [ ] `stage-3a-notifications` - notifications migration + WS invalidation wiring
- [ ] `stage-3a-auth` - auth-shadow query ownership (`useCurrentUser`)

### Stage 3b - Mid risk domains
- [ ] `stage-3b-groups` - full groups queries/mutations + slim context
- [ ] `stage-3b-rides` - rides queries/mutations + WS invalidation
- [ ] `stage-3b-bookings` - bookings summaries/manifest/mutations
- [ ] `stage-3b-passengers` - passenger requests/search/infinite/mutations
- [ ] `stage-3b-uploads` - presigned upload flows via mutations
- [ ] `stage-3b-createride` - migrate `useCreateRide` op-token flow to RQ/signal

### Stage 3c/3d - High impact
- [ ] `stage-3c-admin` - admin domain rebuild off `useAdminFetch`
- [ ] `stage-3d-chat` - standalone chat migration (infinite + optimistic + WS cache sync)

### Stage 4/5 - Tests and cleanup
- [ ] `stage-4-msw` - MSW infra setup
- [ ] `stage-4-tests` - migrate target test to MSW
- [ ] `stage-5-cleanup` - cleanup + deferred docs + lint sweep
- [ ] `verify` - per-PR verify gates

---

## B) Tier-1 Senior FE Architecture - Remaining

### Stage A - OpenAPI Codegen
- [ ] `tier1-a-codegen` - orval types+axios flow + CI regen gate

### Stage B - Bundle Budget
- [ ] `tier1-b-bundle` - visualizer + size-limit + manualChunks + phased budgets

### Stage C - Accessibility
- [ ] `tier1-c-a11y-setup`
- [ ] `tier1-c-a11y-auth`
- [ ] `tier1-c-a11y-rides`
- [ ] `tier1-c-a11y-bookings`
- [ ] `tier1-c-a11y-groups`
- [ ] `tier1-c-a11y-chat`

### Stage D - Web Vitals + Sentry RUM
- [ ] `tier1-d-rum`

### Stage E - Forms (`react-hook-form + zod`)
- [ ] `tier1-e-form-login`
- [ ] `tier1-e-form-register`
- [ ] `tier1-e-form-verify`
- [ ] `tier1-e-form-creategroup`
- [ ] `tier1-e-form-createride`
- [ ] `tier1-e-form-searchrides`
- [ ] `tier1-e-form-messagethread`
- [ ] `tier1-e-form-chatpopup`

### Stage F - React Compiler
- [ ] `tier1-f-compiler-setup`
- [ ] `tier1-f-compiler-presentational`
- [ ] `tier1-f-compiler-rq-hooks`
- [ ] `tier1-f-compiler-pages`
- [ ] `tier1-f-compiler-cleanup`

---

## C) Tier-2 Senior FE Hardening - Remaining

- [ ] `tier2-s1-csp` - security headers + HTTP/2 + sourcemap hardening finish
- [ ] `tier2-s2-dependabot` - Dependabot + security CI gate
- [ ] `tier2-s2-sbom` - SBOM generation + release artifact
- [ ] `tier2-s3-xss` - `react/no-danger` + sanitization wrapper
- [ ] `tier2-s4-be-version` - backend optimistic concurrency
- [ ] `tier2-s4-fe-version` - frontend optimistic concurrency UX/cache handling
- [ ] `tier2-s5-waterfall-audit` - Stage-3 waterfall audits
- [ ] `tier2-s6-throttle` - global client-side throttle
- [ ] `tier2-s7-assets` - asset hardening (image/i18n/preconnect)
- [ ] `tier2-s8-runbook` - frontend performance runbook
- [ ] `tier2-docs` - cross-cutting FE hardening docs

---

## Recommended Execution Order (Short)

1. RQ Stage 1 finalization -> Stage 3a/3b
2. Tier-2 quick wins (`S.1`, `S.2`, `S.3`)
3. Tier-2 concurrency (`S.4` backend then frontend)
4. RQ Stage 3c (admin), then 3d (chat standalone)
5. RQ Stage 4/5 verify+cleanup
6. Tier-1 A/B/D
7. Tier-1 C/E
8. Tier-1 F + Tier-2 S.8/docs
