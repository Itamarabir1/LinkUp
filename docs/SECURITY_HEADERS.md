# Security Headers Rollout (S.1)

This document describes the edge hardening policy for `nginx` and how to safely move CSP from monitoring mode to enforcement.

## Headers and rationale

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

- `Content-Security-Policy-Report-Only`
  - Monitors potential script/resource violations without blocking users.
  - Includes `report-uri` for violation collection and policy tuning.

## CSP origins: how to add a new third-party

1. Identify exact endpoint(s) used by runtime (`script-src`, `connect-src`, `img-src`, etc.).
2. Add the minimal required origin to the correct directive in `nginx/nginx.conf`.
3. Keep the policy in `Report-Only` until violation logs are stable.
4. Verify no wildcard can be replaced by a specific host.
5. Document why this origin is required and who owns it.

Do not add broad wildcards as a shortcut. Prefer explicit hosts and protocol-specific entries.

## Why Report-Only first

- Avoids production breakage from false positives or missing origins.
- Provides real traffic evidence before blocking.
- Enables safe iterative tightening while users continue normal flows.

## Promotion process to enforcing CSP

1. Deploy `Content-Security-Policy-Report-Only` and collect reports for 7 days.
2. Review violations; fix app/resource loading or update policy minimally.
3. Re-run smoke tests for login, chat, maps, uploads, notifications.
4. Replace header name with enforcing mode:
   - from `Content-Security-Policy-Report-Only`
   - to `Content-Security-Policy`
5. Keep `report-uri` for visibility after enforcement.
6. Roll back quickly if unexpected blocking appears.

## Post-deploy commands

Recreate nginx:

```bash
docker compose --env-file backend/.env --env-file frontend/.env up -d --no-deps --force-recreate nginx
```

Validate response headers:

```bash
curl -I https://linkup.itamarabir.com | grep -E "HTTP|strict|x-content|x-frame|referrer|permissions|content-security-policy"
```
