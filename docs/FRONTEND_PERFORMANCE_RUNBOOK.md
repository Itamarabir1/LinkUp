# Frontend Performance Runbook

## Overview
This runbook describes the investigation order for frontend performance issues in LinkUp.
Use it when Sentry RUM shows regressions or users report slowness.

---

## Section 1 — Triage (5 minutes)

**Is it slow for everyone or one user?**
- Check Sentry RUM -> Performance -> LCP/INP percentiles
- If p75 > p50 significantly -> affects many users
- If single user -> check their device/network

**Which metric is regressing?**
- LCP > 2.5s -> loading/render issue
- INP > 200ms -> interaction issue
- CLS > 0.1 -> layout shift

---

## Section 2 — Network Layer

**Tools:** DevTools Network tab, Sentry RUM TTFB

**What to look for:**
- Waterfall of sequential requests (N+1 pattern)
- Large bundle chunks blocking render
- Missing preconnect hints for third-party origins

**Common fixes:**
- Add `useQueries` for parallel fetches
- Check `manualChunks` in `vite.config.ts` for unexpected large chunks
- Add preconnect hints in `index.html`

---

## Section 3 — Render Layer

**Tools:** React DevTools Profiler -> "Why did this render?"

**What to look for:**
- Components re-rendering on every keystroke
- Missing `useMemo`/`useCallback` on expensive computations
- Large lists without virtualization

**Common fixes:**
- Add `staleTime` to RQ queries to reduce refetch
- Extract stable callbacks with `useCallback`
- Check WS event handlers — invalidations should be specific

---

## Section 4 — Bundle Layer

**Tools:** `npm run analyze` -> opens `dist/stats.html`

**What to look for:**
- Unexpected libraries in main chunk
- Duplicate dependencies
- Large chunks that should be lazy-loaded

**Common fixes:**
- Add entry to `manualChunks` in `vite.config.ts`
- Use `React.lazy()` for route-level splitting
- Run `npm run size` to check against budget

---

## Section 5 — Decision Tree

```text
LCP > 2.5s on >25% of sessions
  -> Check image loading (eager vs lazy)
  -> Check i18n bundle size (lazy namespaces)
  -> Check preconnect hints

INP > 200ms
  -> React Profiler -> find slow commit
  -> Check WS handlers — too many invalidations?
  -> Check throttle.ts — requests queuing?

CLS > 0.1
  -> Check image dimensions (width/height attrs)
  -> Check font loading (preconnect to fonts.googleapis.com)

API p95 > 500ms
  -> Backend issue — check /readyz + Sentry backend errors
  -> Check RQ staleTime — too aggressive refetch?
```

---

## Section 6 — Available Dashboards

- **Sentry RUM:** Web Vitals (LCP/INP/CLS p75)
- **Bundle:** `npm run analyze` -> `dist/stats.html`
- **Bundle Budget:** `npm run size`
- **Backend Health:** `curl https://linkup.itamarabir.com/livez`

---

## Section 7 — Rollback

If a deployment causes performance regression:

1. Identify via Sentry release comparison
2. `git revert <merge SHA>`
3. Push to main -> CI deploys automatically
4. Verify via `curl https://linkup.itamarabir.com/livez`
