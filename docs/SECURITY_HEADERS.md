# Security Headers & CSP (`nginx`/edge)

This document describes the edge hardening policy for Compose **edge nginx** and how CSP fits with broader **XSS defense-in-depth** (browser policy + app hygiene + API input policy).

**Template:** [`nginx/nginx.conf.template`](../nginx/nginx.conf.template) (committed). The CSP `report-uri` line uses **`${SENTRY_REPORT_URI}`** — substituted at deploy time only (never commit the ingestion URL).

**Rendered file:** `nginx/nginx.conf` is **generated** (`gitignored`). Set **`SENTRY_REPORT_URI`** in **`backend/.env`** (same key EC2 deploy reads), then run:

```bash
bash scripts/ops/render-nginx-conf.sh
```

---

## Relation to XSS mitigation

**CSP does not replace escaping or input policy**; it constrains what the browser will load/run when a page is served. Linkup stacks:

- **Edge CSP** (this doc): restricts scripts, frames, connects, etc., for the web app HTML shell.
- **Frontend:** ESLint **`react/no-danger`**, centralized **`sanitizeHtml()`** (`DOMPurify` allowlist) — see **`docs/ENGINEERING_HIGHLIGHTS.md`** / **`frontend/README.md`**.
- **Backend chat:** plaintext-only messages + **`MessageCreate.reject_html`** — **`docs/FEATURE_DECISIONS.md`** (`#chat-plaintext`).

**`script-src`:** `'unsafe-inline'` was **removed** — inline bootstraps that used to live in [`frontend/index.html`](../frontend/index.html) were moved to **[`frontend/public/bootstrap.js`](../frontend/public/bootstrap.js)** (served as **`/bootstrap.js`** from the static root). In `index.html`, load order is **`/bootstrap.js` then `/config.js`** so `lang`/`dir`/`data-theme` apply before runtime config is evaluated.

**`style-src`:** still includes **`'unsafe-inline'`** (Vite/CSS-in-modules pragmatism); tightening styles further is a separate effort.

For **nonces** on the main Vite bundle without edge rewriting, see **“CSP and static SPA”** below.

---

## HTML shell: `public/bootstrap.js`

The file is copied verbatim into `dist/` and nginx `html` root. **`index.html` loads scripts in this order: `/bootstrap.js` first, then `/config.js`** — language, direction, and theme must bootstrap from storage before the runtime config script runs (see **Relation to XSS mitigation** above for CSP rationale). It runs two IIFEs (formerly inline in `index.html`):

1. **`linkup-lang`** → `document.documentElement` `lang`/`dir` when stored value is `en`.
2. **`linkup-theme`** → `data-theme` from storage or `prefers-color-scheme`.

No inline `<script>` bodies remain in the shell for these concerns, so **`script-src` does not need `'unsafe-inline'`** for them.

---

## Headers and rationale

### TLS / HTTP (Compose `nginx`)

Canonical template: [`nginx/nginx.conf.template`](../nginx/nginx.conf.template) → rendered `nginx/nginx.conf` locally via [`scripts/ops/render-nginx-conf.sh`](../scripts/ops/render-nginx-conf.sh). The **`443`** server block uses **`listen 443 ssl`** (the `http2` keyword is **not** present in the template) — effectively **HTTP/1.1 over TLS** unless you add **`http2`** to the directive. After any change to ALPN/HTTP version, re-smoke **WebSockets** (`/api/v1/…` upgrade, `/ws`) and large uploads.

- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - Forces browsers to use HTTPS after first successful secure visit.
  - `preload` is intentionally excluded for now to avoid lock-in risk on future/non-HTTPS subdomains.

- `X-Content-Type-Options: nosniff`
  - Prevents MIME type sniffing and reduces script/style confusion attacks.

- `X-Frame-Options: DENY`
  - Blocks clickjacking by disallowing framing.

- `Referrer-Policy: strict-origin-when-cross-origin`
  - Sends full referrer only same-origin, origin-only cross-origin.

- `Permissions-Policy: geolocation=(self), microphone=(), camera=(), payment=(self)`
  - Restricts browser feature access to trusted contexts.

- **`Content-Security-Policy` (enforcing)**
  - Browser **blocks** disallowed loads; violations can still be reported if `report-uri` is configured.

- **`Cross-Origin-Opener-Policy` / `Cross-Origin-Embedder-Policy`**
  - Tuned for **Google OAuth popup** compatibility (`same-origin-allow-popups`, `unsafe-none`). See **`docs/FEATURE_DECISIONS.md`** (`#oauth-popup-coop`).

### CSP highlights (Compose `nginx`)

- **`script-src`:** **`'self'`** plus required third-party script hosts (Google gstatic/APIs, Sentry browser CDN, GTM, Google accounts) — **no** `'unsafe-inline'`; same-origin **`/bootstrap.js`**, **`/config.js`**, and Vite chunk URLs are covered by **`'self'`**.
- **`connect-src`:** API self, **`wss://`** chat host, Firebase (HTTP + **`wss://*.firebaseio.com`**), **`https://*.sentry.io`**, FCM registration, GA, uploads host, etc.
- **`frame-src`:** Stripe (`js.stripe.com`) and **`https://accounts.google.com`** (GIS / Sign-In iframe flows).
- **`form-action`:** self + Stripe checkout host.
- **`report-uri`:** Sentry **CSP / security reports** ingestion URL for the project (region-specific ingest host); prefer **injecting via deploy secrets** rather than committing keys.

---

## CSP origins: how to add a new third-party

1. Identify exact endpoint(s) used by runtime (`script-src`, `connect-src`, `img-src`, `frame-src`, etc.).
2. Add the minimal required origin to the correct directive in **`nginx/nginx.conf.template`**, rerun **`scripts/ops/render-nginx-conf.sh`**, then retest the Compose edge nginx server.
3. After a policy change: smoke **login**, **maps**, **chat**, **uploads**, **billing/Stripe**, **push/analytics**.
4. Verify no wildcard can be replaced by a specific host where practical.
5. Document why this origin is required and who owns it.

Do not add broad wildcards as a shortcut. Prefer explicit hosts and protocol-specific entries.

## Historical: Report-Only first

The project intentionally used **`Content-Security-Policy-Report-Only`** first to collect **`report-uri`** telemetry and tune origins **before** enforcement. Production Compose nginx is now on **enforcing** **`Content-Security-Policy`**; keep monitoring Sentry CSP reports after changes.

---

## CSP and static SPA (nonces)

The web client is a **Vite static build** served by nginx (`frontend/Dockerfile` copies **`dist/`**). There is **no SSR** that can inject a fresh **`nonce`** into HTML per request unless you add **edge HTML rewriting**, a tiny **SSR gate** for `index.html`, or move to **`'sha256-'` hashes** for fixed inline blobs. **Bootstrap snippets** are no longer inline: they live in **`/bootstrap.js`**, so **`script-src` can stay strict** without hashes for that path. If you add new **inline** scripts to `index.html`, you must either allow them via **`'sha256-…'`** (see historical tooling discussions in repo history) or move them to external files whitelisted by **`'self'`**.

---

## Rollback / promotion checklist

If a deploy breaks legitimate third-party resources:

1. Confirm violations in browser devtools (**Console / Issues**) or Sentry CSP reports.
2. Add the **missing directive entry** minimally, or temporarily restore **`Content-Security-Policy-Report-Only`** alongside enforcing (same policy body) for a short observation window — only if operational risk requires it.
3. Keep **`report-uri`** wired when possible for visibility.

## Post-deploy commands

Recreate nginx:

```bash
docker compose --env-file backend/.env --env-file frontend/.env up -d --no-deps --force-recreate nginx
```

Validate response headers:

```bash
curl -I https://linkup.itamarabir.com | grep -E "HTTP|strict|x-content|x-frame|referrer|permissions|content-security-policy"
```

You should see **`Content-Security-Policy:`** (enforcing). If you only see **`Content-Security-Policy-Report-Only`**, the edge config was not rolled out or differs per environment.
