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

Canonical template: [`nginx/nginx.conf.template`](../nginx/nginx.conf.template) → rendered `nginx/nginx.conf` locally via [`scripts/ops/render-nginx-conf.sh`](../scripts/ops/render-nginx-conf.sh). TLS tuning is extracted into [`nginx/snippets/ssl-params.conf`](../nginx/snippets/ssl-params.conf) and included via `include /etc/nginx/snippets/ssl-params.conf;` — single auditable file for all cipher/session/OCSP directives. The **`443`** server block uses **`listen 443 ssl`** with **`http2 on`** (HTTP/2 multiplexing + header compression). After any change to ALPN/HTTP version, re-smoke **WebSockets** (`/api/v1/…` upgrade, `/ws`) and large uploads.

#### SSL hardening (`nginx/snippets/ssl-params.conf`)

| Directive | Value | Rationale |
|-----------|-------|-----------|
| `ssl_protocols` | `TLSv1.2 TLSv1.3` | Drops legacy TLS 1.0/1.1 |
| `ssl_prefer_server_ciphers` | `on` | Forces server cipher order for TLS 1.2 |
| `ssl_ciphers` | ECDHE-only AEAD suite | Forward secrecy, no CBC/3DES/RC4/DHE |
| `ssl_ecdh_curve` | `X25519:secp384r1:secp256r1` | Fastest modern curves first |
| `ssl_session_cache` | `shared:SSL:10m` | ~40K sessions, avoids full handshake on reconnect |
| `ssl_session_timeout` | `1d` | Session reuse window |
| `ssl_session_tickets` | `off` | Tickets undermine forward secrecy without key rotation |
| `ssl_stapling` | `on` | OCSP stapling — faster handshake, no client-to-CA privacy leak |
| `ssl_stapling_verify` | `on` | Validates stapled OCSP response against `chain.pem` |
| `resolver` | `1.1.1.1 8.8.8.8` | For OCSP responder DNS resolution |

#### Certbot renewal (zero-downtime)

Port 80 server block includes `location /.well-known/acme-challenge/` serving from `/var/www/certbot` — certbot webroot mode works without stopping nginx. The volume is mounted read-only in `docker-compose.yml`.

- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - Forces browsers to use HTTPS after first successful secure visit.
  - `preload` enables submission to the [HSTS Preload List](https://hstspreload.org/).

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
- **`connect-src`:** API self, **`https://accounts.google.com`** (GIS SDK XHR — `/gsi/log`, `/gsi/status`), **`wss://`** chat host, Firebase (HTTP + **`wss://*.firebaseio.com`**), **`https://*.sentry.io`**, FCM registration, GA, maps, uploads host.
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

## Frontend internal nginx headers (`frontend/nginx.conf`)

The internal nginx inside the frontend container (port 8080, serving the SPA) adds defense-in-depth headers at the `server` block level:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(self)` |

**Intentionally omitted from the internal nginx:** CSP and HSTS — these are set by the outer Compose edge nginx (`nginx/nginx.conf.template`). Duplicating them in the frontend container would cause double-header conflicts or break the local dev environment where the outer nginx is not present.

These headers protect against MIME sniffing, clickjacking, and referrer leakage even when the frontend container is accessed directly (e.g., during development or if the outer nginx proxies without overriding headers).

---

## Backend API CSP (FastAPI middleware)

The FastAPI `SecurityHeadersMiddleware` (`backend/app/core/middleware/security_headers.py`) adds a **Content-Security-Policy** header to every API response as a defense-in-depth layer. Two policies are used:

**API responses (JSON):**

```
default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'
```

This is the strictest possible CSP — blocks all resource loading. If a browser renders an API response directly (bookmarked URL, open-in-new-tab), no scripts or frames can execute.

**Swagger UI / ReDoc (`/docs`, `/redoc`, `/openapi.json`):**

```
default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; font-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none'
```

Relaxed to allow Swagger/ReDoc JS/CSS assets. Only active when `API_DOCS_ENABLED` is true (disabled in production).

**Layering summary:**

| Layer | CSP? | Scope |
|-------|------|-------|
| Edge nginx (`nginx/nginx.conf.template`) | Enforcing, full SPA policy | Browser-rendered content (HTML/JS/CSS) |
| Backend middleware (`security_headers.py`) | Enforcing, strict `none` policy | API JSON responses |
| Frontend nginx (`frontend/nginx.conf`) | No (intentional) | Avoids double-header conflicts |

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
