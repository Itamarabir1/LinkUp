# LinkUp — הדגשים הנדסיים (Portfolio / Senior)

**שם הקובץ:** `docs/ENGINEERING_HIGHLIGHTS.md` (בשורש הפרויקט, תחת `docs/`).

**סיכום מלא ומדויק ל-Billing refactor** (לפני/אחרי, state machine, reconciler, idempotency DB, webhooks, השוואת פוסט Kafka, טסטים): [`BILLING_REFACTOR_SUMMARY.md`](BILLING_REFACTOR_SUMMARY.md).

מסמך זה אוסף **במקום אחד** את הפיצ’רים, הטכנולוגיות, הדפוסים וההחלטות שמיועדות ל**סקייל, אמינות ותחזוקה** — כדי להציג את הפרויקט ברמת מומחה.  
*זה סיכום “להצגה”, לא מיפוי כל שורה בקוד; אחרי סקירה מול ה-repo הוכנסו גם workers, AI, FCM, Brevo, Google, **חיזוק auth ועומס מקבילי**, **JWT עם `jti` + denylist ב-Redis אחרי logout**, **Idempotency-Key לבקשת הצטרפות מחיפוש ובשליחת הודעת צ’אט (Redis, Stripe-style; בפרונט מפתח יציב ב-ref + מיזוג `message_id` מול WS + UI אופטימי לשליחה עם `ChatListRow` / `applyInboundRealMessage`)**, **Circuit Breaker in-memory משותף (`app/infrastructure/circuit_breaker.py`) — מעגלים נפרדים ל-Google Maps Platform (Geocoding / Directions / Distance Matrix) ולשליחת מייל Brevo (Transactional API) עם מדדי Prometheus ייעודיים (`geo_circuit_breaker_state`, `brevo_circuit_breaker_state`) וחשיפת מצב ב־`GET /api/v1/health`**, **k6**, **ריפקטור async משמעותי ב-passengers/bookings/rides**, **ריפקטור ארגון בפרונט**, **מסך אדמין פנימי (React + `/api/v1/admin`)**, **מעבר ארכיטקטוני ל-React Email renderer (Node.js/Express)**, **מדיה: S3 + CloudFront (אופציונלי) ואווטארים ב-prefix גרסתי immutable**, ו**i18n (עברית/אנגלית) + פורמט תאריכים לפי לוקאל + fallbacks לשגיאות API דרך `common:err_*` + איחוד פונטים ב־CSS Modules**.*

**לראיון — מיפוי שורת CV ↔ איפה בקוד:** [`docs/internal/INTERVIEW_TECH_STACK_MAP.md`](internal/INTERVIEW_TECH_STACK_MAP.md).

**לראיון — ניווט לפי נושא + טבלת Why / Alternatives / Trade-offs (מקביל למסמך הזה):** [`docs/internal/INTERVIEW_PLAYBOOK.md`](internal/INTERVIEW_PLAYBOOK.md) · [`FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md).

לפרטים טכניים עמוקים יותר: `../ARCHITECTURE.md`, `ERRORS.md`, `architecture/REALTIME.md`, `architecture/EVENTS.md`, `architecture/DATABASE.md`, `architecture/API.md`, `backend/docs/GOOGLE_OAUTH.md`.

---

## Latest architecture updates

- **Production hardening checklist (completed):**
  - all runtime images build in CI and are pulled from GHCR on deploy
  - single-EC2 rolling deploy with health-gated rollback (no full downtime window)
  - compose env source-of-truth hardened with multiple `--env-file` inputs
  - RabbitMQ consumers upgraded to self-healing behavior on iterator/channel close
  - frontend runtime config moved to startup-time `envsubst` (`window.__APP_CONFIG__`)
  - HTTPS redirect behavior hardened for loopback health checks
  - deploy-time JWT secret sync between backend and chat-ws
  - OAuth popup compatibility fixed with nginx COOP/COEP headers
  - deploy disk pressure mitigated with aggressive image prune strategy
  - production endpoint stabilized at `https://linkup.itamarabir.com`
  - local runbook standardized with root `Makefile` wrapper (`make up/down/build/...`) so Compose always includes the required env-file flags
  - `pgbouncer` root `.env` coupling removed from compose service definition; deploy runtime vars are resolved from CI `--env-file backend/.env --env-file frontend/.env`
  - EC2 deploy script now exports `POSTGRES_DB` alongside `POSTGRES_USER`/`POSTGRES_PASSWORD` before compose rollout for deterministic pgbouncer env resolution
  - Edge **enforcing CSP** on Compose: **`nginx/nginx.conf.template`** → rendered **`nginx/nginx.conf`** ([**`scripts/ops/render-nginx-conf.sh`**](../scripts/ops/render-nginx-conf.sh) locally; CI `envsubst '${SENTRY_REPORT_URI}'` on EC2; **`SENTRY_REPORT_URI`** in **`backend/.env`**). **`Content-Security-Policy`** (was Report-Only) with curated **`script-src`** ללא **`'unsafe-inline'`** (קובץ **`public/bootstrap.js`** [`frontend/public/bootstrap.js`](../frontend/public/bootstrap.js) כ־**`/bootstrap.js`** לפני **`/config.js`**); **`connect-src`** / **`img-src`** for Firebase, Sentry ingest, GA/GTM, maps, uploads; **`frame-src`** includes Stripe + **`accounts.google.com`** (GIS); **`style-src`** עדיין עם **`'unsafe-inline'`** ל-Vite/CSS; **`report-uri`** from env (no hardcoded ingestion URL in Git); CSP complements app/API XSS controls — see **`docs/SECURITY_HEADERS.md`**. (**K8s:** sync **`k8s/frontend/nginx-configmap.yaml`** if that path is used.)

- **Supply chain baseline (Dependabot):** `.github/dependabot.yml` opens scheduled dependency PRs for:
  - npm (`/frontend`, weekly)
  - pip (`/backend`, weekly)
  - docker (monthly, per Dockerfile location): `/backend`, `/frontend`, `/infrastructure/pgbouncer` — **fixed:** Dependabot was looking in **`/`** but Dockerfiles live only in those subdirectories, so updates must target those paths.

- **Realtime badges — review alignment:** `ChatContext.handleInvalidate` for **`notifications`**: `refreshUnreadNotifications` + custom **`NOTIFICATIONS_REFRESH_EVENT`** + conditional **`linkup:user-event`** `{ event, user_id }`; **`WebSocketProvider.send(..., db=None)`** matches **`BaseNotificationProvider`**. פריימי **`unread_count`** על צ'אט נשארו תחת **`ChatPresenceEventSchema`** כדי **`processChatWebSocketMessage.ts`** יישאר ללא שינוי במסגרת הריפקטור.

- **Nav unread affordance (frontend shell):** ב־**[`Layout/index.tsx`](../frontend/src/components/Layout/index.tsx)** — כשקיימת תגית מספרית (`messagesBadge` / `notificationsBadge` מ־**`useLayoutShell`**), לינקי הודעות והתראות מקבלים גם את **`.iconBtnUnread`** ב־[**`Layout.module.css`**](../frontend/src/components/Layout/Layout.module.css) (צבע **primary**, רקע **primary-light**, גבול **primary-soft-border**) — אותה שפה ויזואלית כמו כפתור החיפוש; ללא שינוי ב־`ChatContext` / API.

- **Centralized EC2 deploy (`workflow_run`):** **[`.github/workflows/deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml)** — אחרי **Backend CI** / **Frontend CI** / **Chat-WS CI** / **Email renderer CI** על **`main`** ב־**success**; SSH (אותם **`EC2_*`**), compose מלא, smoke פנימי ל־**`linkup_frontend`** (**`config.js`**) ול־**`linkup_email_renderer`** (**`/health`**) לפני gate ל־**`backend`**, fallback ל־**`backend:latest`** אם תג SHA חסר ב־GHCR או ב־rollback. פירוט: **[`docs/DEPLOYMENT.md`](DEPLOYMENT.md)**, **[`README.md`](../README.md)**.

- **Passenger ride search — temporal filters:** **`RideSearchRequest`** / **`GET …/search-rides`**: **`departure_date`** (Jerusalem calendar day ב־UTC window), **`departure_time`** (±2h), או טווח סגור עם **`departure_time_to`**; **הדדיות** → **422**. CRUD **`find_rides_by_coordinates`**; פרונט **`buildManualRideSearchParams`** + **`buildParamsFromAiResult`** לפי **`searchMode`**; Orval מאותו openapi snapshot; טסטים: **`tests/domain/test_ride_search_request.py`**, **`rideSearchParams.test.ts`**.

- **Chat outbound: idempotency + optimistic UI + merge (frontend):** Message list state is **`ChatListRow[]`** ([`types/chatList.ts`](../frontend/src/types/chatList.ts)) — **`confirmed`** wraps **`MessageResponse`**, **`pending`** carries **`client_message_id`** (UUID) for the in-flight bubble. **`useMessageThread`** and **`useChatPopup`** append a pending row on send, clear input, then **`consumeOrCreateKey` / `resetOutboundKey`** ([`outboundIdempotencyKey.ts`](../frontend/src/utils/outboundIdempotencyKey.ts)) with **`sendMessage`**; on success or inbound **`MessageResponse`**, **`applyInboundRealMessage`** drops the correlated pending and delegates dedupe to **`appendMessageDedupById`** ([`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts)); **`removePendingByClientId`** on REST failure restores text. Full thread path: **`outboundPendingRef`** in **`useMessageThread`** + **`processChatWebSocketMessage`** reconciles own messages from WS before or after REST. **`isChatIdempotencyKeyMismatch`** ([`apiError.ts`](../frontend/src/utils/apiError.ts)) unchanged. Pending bubbles: reduced opacity + **`Loader2`** spinner; read receipts only on **`confirmed`** own messages.
- **chat-ws inbound hardening (Go):** after WebSocket **`Upgrade`**, **`conn.SetReadLimit(2048)`** caps full inbound message bytes (protects CPU/memory); per-connection **`golang.org/x/time/rate`** limiter (**limit 30/s, burst 60**) gates **`typing_start`/`typing_stop`** before Redis publish — **`ping`** (`RefreshPresence` + `pong`) is exempt; over-limit typing drops silently (connection stays open). **`chat-ws/internal/hub/handler.go`**, **`chat-ws/ARCHITECTURE.md`**, **`docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md`** §7.

- **Outbox worker horizontal scale — `SKIP LOCKED`:** `OutboxRepository.get_pending_events` uses **`with_for_update(skip_locked=True)`** on **`outbox_events`** so parallel **`notification-worker`** instances do not block each other on the same DB row (`backend/app/infrastructure/outbox/repository.py`). Narrative + trade-offs: **`docs/FEATURE_DECISIONS.md#outbox-skip-locked`**, **`docs/architecture/EVENTS.md`**, ADR backend §4.

- **RabbitMQ consumer graceful drain:** `ConsumerSupervisor` in `rabbitmq/consumer.py` tracks per-message **`asyncio` tasks**, stops accepting new deliveries, then **`asyncio.wait`** with a drain timeout (**30s**) before cancelling stragglers — safer deploy/`docker compose stop`. See **`docs/FEATURE_DECISIONS.md#rabbitmq-graceful-drain`**.

- **Frontend bundle splitting (Vite):** **`vite.config.ts`** defines **`rollupOptions.output.manualChunks`** — isolates **`react-vendor`** (React + router), **`query`** (TanStack Query), **`firebase`**, **`sentry`**, **`i18n`**, **`forms`** (RHF + zod), **`charts`** (recharts) from the app graph to improve **cache reuse** and cap main-thread parse cost; **`chunkSizeWarningLimit: 700`** (kB) documents the expected post-minify ballpark; **`rollup-plugin-visualizer`** writes **`dist/stats.html`** for bundle treemaps in production builds.

- **Route-level lazy loading:** `frontend/src/App.tsx` uses **`React.lazy` + `Suspense`** for essentially all user-facing and **admin** pages — the initial download avoids pulling every screen until navigation (Pairs with manual chunks above).

- **Dev-only accessibility tooling:** `main.tsx` dynamically imports **`@axe-core/react`** only when **`import.meta.env.DEV`** — runtime a11y checks without shipping the dependency to production.

- **Web Vitals → Sentry custom metrics:** in production **`main.tsx`**, **`web-vitals`** (**CLS**, **LCP**, **INP**) report into **`sentry.metrics.distribution`** as **`web_vitals.*`** (CLS unit `none`, LCP/INP `millisecond`) alongside BrowserTracing/Replay sampling — ties field Core Web Vitals to the same observability vendor as errors.

- **Repository operational scripts (`scripts/ops/`):** smoke/CI-adjacent helpers beyond DLQ replay — **`check-migration-head.sh`** (asserts **`alembic current` is `(head)`**), **`pgbouncer-smoke.sh`**, **`redis-sentinel-smoke.sh`**, **`firebase-modelb-smoke.sh`**; **`rabbitmq-dlq-replay.py`** documented in **`docs/architecture/EVENTS.md`**. Prefer running migration checks from **`backend/`** per script headers.

- **Root `Makefile` quality-of-life:** wraps **`docker compose --env-file backend/.env --env-file frontend/.env`** for **`up` / `down` / `migrate` / `logs`**; **`admin-grant`** / **`admin-revoke`** / **`admin-check`** (with **`EMAIL=`**) run **`psql`** against the Compose **`db`** service to flip or verify **`users.is_admin`**. See repo root **`Makefile`**.

- **XSS hardening baseline (frontend + edge defense-in-depth):** enforced `react/no-danger` as blocking lint rule and centralized **`sanitizeHtml()`** in `frontend/src/utils/sanitize.ts` (`DOMPurify` allowlist: `b`, `i`, `em`, `strong`, `a`, `br`; `href`, `target`, `rel`); paired with **enforcing browser CSP** on edge nginx (**`docs/SECURITY_HEADERS.md`**) and **plaintext-only chat** validation in the API (**`FEATURE_DECISIONS`** `#chat-plaintext`).

- **SLOs & Error Budgets observability baseline:** metrics surface הורחב מ-backend-only ל-backend + workers (`9091/9092/9093`) עם מדדי domain/reliability (auth, rides, bookings, billing, RabbitMQ, outbox, geo cache/circuit-breaker, S3, AI). זה מאפשר להגדיר SLOs רשמיים (availability/latency/reliability) ולנהל release decisions לפי error-budget consumption במקום לפי אינטואיציה.
- **RabbitMQ PR1 reliability guardrails:** consumer runtime now includes supervision + draining states (`RUNNING -> DRAINING -> STOPPED`) and queue-scoped `x-death` parsing for retry observability. Workers run long-lived loops through `run_supervised` with bounded retries (`max_retries`) to prevent silent infinite crash loops.
- **RabbitMQ PR2 topology hardening:** messaging path split to role-specific clients — `rabbit_client` (API publish), `outbox_rabbit_client` (Outbox publish), `worker_rabbit_client` (worker consume/scheduler). Worker consumers share one worker connection but run isolated channels per queue; queue behavior moved to centralized `QueueSpec` (`backend/app/infrastructure/rabbitmq/topology.py`).
- **RabbitMQ PR3 pure DLX/TTL retry:** manual republish retry loop removed from worker path. Retry now broker-native (`retry_exchange` + `<queue>.retry` with `x-message-ttl`) and attempt counting uses queue-scoped `x-death`; workers only `nack(requeue=False)` for transient failures and route terminal failures to queue DLQ.
- **RabbitMQ PR4 DLQ operability:** `notification-worker` now runs periodic DLQ depth monitoring (`run_dlq_monitor`) with warning/critical thresholds and structured logs for early detection of stuck consumers/poison traffic.
- **RabbitMQ PR5a tests in CI:** נוספו בדיקות ייעודיות ל-reliability path (`backend/tests/infrastructure/test_rabbitmq_reliability.py`) ונוספה ריצתן המפורשת ל-`backend-ci` לפני ריצת כלל הטסטים.
- **RabbitMQ PR5b replay tooling:** נוסף כלי אופרטיבי `scripts/ops/rabbitmq-dlq-replay.py` ל-replay מבוקר של הודעות DLQ חזרה לתור הראשי, עם `--queue`, `--limit`, ו-`--dry-run`.
- **Rate limiting split by threat model (Token Bucket + Sliding Window):** המימוש שודרג מ-fixed window (`INCR+EXPIRE`) לשני Lua scripts אטומיים: `rate_limit_auth` עם Sliding Window (anti-bruteforce ללא burst) ו-`rate_limit_chat` עם Token Bucket (burst-tolerant לפרודוקט UX), כולל `X-RateLimit-*` headers ו-fail-open ב-Redis outage.
- **Probe routing hardening in nginx (`/livez` + `/readyz`):** `/livez` ו-`/readyz` הועברו ל-`location =` exact-match כדי למנוע fallback ל-frontend `location /`; `/readyz` הוקשח ל-loopback בלבד (`allow 127.0.0.1`, `allow ::1`, `deny all`) כדי לא לחשוף לציבור טופולוגיית תלות פנימית (DB/Redis/RabbitMQ/circuit breakers), בעוד `/livez` נשאר public ל-uptime probes.
- **Production observability consoles — שני כלים נפרדים (Sentry + Better Stack):** **Sentry** (מוצר [`sentry.io`](https://sentry.io)) ו־**Better Stack** (מוצר [`uptime.betterstack.com`](https://uptime.betterstack.com)) הם **ספקים שונים** — לא אותו שירות: Sentry = שגיאות/ביצועים/ריפליי/RUM בקוד; Better Stack = בדיקות זמינות חיצוניות + דפי אירועים. בנוסף ל־Prometheus/Grafana תחת profile `monitoring` ולכל האינטגרציות בקוד (**SDK**, **RUM + Replay**, **Web Vitals**, **`report-uri`** ל‑CSP), בפרודקשן: **[קישור Issues ב־Sentry](https://itamar-abir.sentry.io/issues/?project=4511256490606592&statsPeriod=14d)**; **[מוניטורים ב־Better Stack](https://uptime.betterstack.com/team/t520754/monitors)**; [אירוע לדוגמה](https://uptime.betterstack.com/team/t520754/incidents/959204833). **שכבת אופס אנושית** שמשלימה self-hosted — פירוט: **`docs/operations/MONITORING.md`**.
- **Persistent audit log (admin + billing):** נוספה טבלת `audit_log` עם אינדקסים לפי actor/resource וזמן, repository ייעודי, וכתיבה מהפעולות האדמיניות הרגישות (`toggle_user_active`, `toggle_user_admin`, `cancel_ride`, `outbox_requeue`) בנוסף ל-`[admin_audit]` בלוגים. ב-billing webhook (`checkout.session.completed`) audit attempt נכתב **לפני** בדיקת idempotency לפי `stripe_event_id`, כך שגם retries/duplicates מתועדים פורנזית.
- **Billing — אידמפוטנטיות checkout ב-Postgres + reconciler + מכונת מצבים:** **`POST /api/v1/billing/checkout`** תומך ב־**`X-Idempotency-Key`** עם טבלה **`idempotency_keys`** (fingerprint + שמירת גוף התשובה, TTL **`BILLING_IDEMPOTENCY_TTL_HOURS`**; **`IDEMPOTENCY_MISMATCH`** אם המפתח לא תואם את ה-fingerprint). **`BillingReconciler`** (APScheduler ב־**`backend/app/core/lifespan.py`** כש־**`BILLING_RECONCILER_ENABLED`** (ברירת מחדל **`true`**; **`false`** משבית), **`pg_try_advisory_lock`**, פרמטרים **`BILLING_RECONCILER_*`** / **`BILLING_PENDING_*`**) מסנכרן תשלומים **`pending`** מול Stripe כשה-webhook מתעכב; מדדי Prometheus **`billing_reconciler_*`**, **`billing_idempotency_hits_total`**. **`validate_transition`** ב־**`state_machine.py`** מונע מעברי סטטוס בלתי חוקיים (**`ILLEGAL_PAYMENT_TRANSITION`**). אדמין: **`GET /api/v1/admin/billing/stale-pending`**, **`POST /api/v1/admin/billing/reconcile/{payment_id}`**. טסטים: **`backend/tests/domain/test_billing_state_machine.py`**, **`backend/tests/domain/test_billing_reconciler.py`**, **`backend/tests/domain/test_billing.py`**, **`backend/tests/api/test_billing_idempotency.py`** (~**22** מקרים ביחד עם `pytest --collect-only`; דורש **`alembic upgrade head`** לפני pytest או **`make test`** מתוך **`backend/`**). פירוט: **[FEATURE_DECISIONS.md — billing-checkout-db-idempotency-reconciler](FEATURE_DECISIONS.md#billing-checkout-db-idempotency-reconciler)**, **[API.md](architecture/API.md)**, **[DATABASE.md](architecture/DATABASE.md)** (**`016_merge015_heads`** ממזג את שני צעדי **015** אחרי **014**).
- **Admin privilege governance hardening:** שינוי הרשאת אדמין (`/api/v1/admin/users/{id}/admin`) תומך כעת ב-`action=grant|revoke|toggle` עם guardrails (חסימת self-demotion ושמירה על לפחות אדמין אחד), ומעשיר audit metadata (`before/after`, `changed`, `target_email`, `reason`) לצורכי תחקור ובקרת גישה.
- **Admin control-plane expansion (P0-P2 baseline):** נוספו `admin/bookings`, `admin/billing/payments`, ו-`admin/system|queues|workers` ב-backend; בפרונט נוספו עמודי `AdminBookings`, `AdminBilling`, `AdminAudit`, `AdminOps`; `audit-log` שודרג ל-pagination + time-range filters, וקריאות רגישות (`admin_outbox_payload_read`, `admin_audit_log_read`) נרשמות כ-audit events.
- **Auth forms hardening (`react-hook-form` + `zod`):** מסכי `Login`/`Register`/`VerifyEmail` הועברו לניהול `useForm` עם `zodResolver`, תוך שמירת behavior parity (אותם API calls וזרימות ניווט). ב-`Register` שדה `PhoneInput` חובר דרך `Controller`, ב-`Login` נשמר prefill מ-`location.state?.email`, ובכל המסכים `formState.isSubmitting` משמש לנעילות submit לצד `error` state נפרד לשגיאות API בלבד.
- **Stage 3a — React Query migration (Geo + Notifications + Auth-shadow):** `useGoogleMapsKey` עבר מ-`useState/useEffect` ל-`useQuery` עם `qk.geo.mapsKey()` (`staleTime/gcTime: Infinity`) תוך שמירת tri-state (`null`/`''`/key) ושגיאות localized; `Notifications.tsx` עבר מ-fetch ידני ל-`useQuery` (`qk.notifications.all`) + invalidate על `linkup-notifications-refresh`; `AuthContext` מסנכרן את `qk.auth.me()` אחרי login/google sign-in, מבצע `queryClient.clear()` ב-logout, ונוסף hook חיצוני `useCurrentUser()` בלי לשבור את `useAuth()` API.
- **Stage 3b — React Query migration (Groups + MyRides):** `GroupContext` הועבר ל-`useQuery` (`qk.groups.list`) + `invalidateQueries` תוך שמירה מלאה על ה-public API של `useGroup()`. עמוד `MyRides` הועבר ל-`useQuery`/`useMutation` (`qk.rides.list`, `mk.rides.cancel`) עם עדכון cache נקודתי ב-cancel והחלפת עדכוני `setState` מ-WS ב-invalidation דטרמיניסטי.
- **Stage 3b Part 2 — React Query migration (MyBookings Driver + Passenger):** `useMyBookingsPassenger` ו-`useMyBookingsDriver` הועברו מ-fetch ידני ל-`useQuery` עם keys scoped לפי משתמש (`qk.bookings.passenger(userId)` / `qk.bookings.driver(userId)`), mutations לפעולות approve/reject/cancel, invalidate על אירועי WS, ו-optimistic updates היכן שבטוח. במקביל נשמרו ללא שינוי `driverStatus` state machine, `useUserEvent`/`useLocationBroadcast` raw hooks, וחוזה ההחזרה של שני hooks עבור `useMyBookings`/`MyBookingsViewModel`.
- **Stage 3c — Admin React Query rebuild:** שכבת `useAdminFetch` הוסרה בפועל; domain hooks נפרדים נוספו תחת `frontend/src/features/admin/queries` ו-`frontend/src/features/admin/mutations` עבור `Users`, `Rides`, `Groups`, `Outbox`, `Health`, `Stats`.
- **Admin lookup flow aligned to RQ on-demand pattern:** `AdminLookup.tsx` הומר מ-manual async `useState` state-machine (`idle/loading/ready/error`) ל-`useMutation` ייעודי עבור `ride`/`booking` lookup, עם שימור מלא של UI parity והפרדת imperative trigger מה-query lifecycle.
- **OpenAPI contract codegen (Orval):** נוסף `frontend/orval.config.ts` שמייצר client/types מ-`frontend/openapi-snapshot.json` ל-`frontend/src/api/generated`, עם mutator משותף (`apiMutator`) מעל axios instance האחיד. התוצרים נכנסים ל-git כ-source-of-truth חוזי מול backend, וב-`frontend-ci` נאכף drift gate ייעודי (`contract-codegen`: `npm run gen:api` + `git diff --exit-code -- src/api/generated/`).
- **Google Sign-In local 403 hardening playbook:** תועד נוהל OAuth מדויק ל-local (`localhost:5173` ב-Authorized JavaScript origins + redirect URIs) יחד עם המלצה ארכיטקטונית לסביבת פיתוח נקייה: client-id ייעודי ל-local דרך `VITE_GOOGLE_CLIENT_ID`.
- **Stage 3d — Chat RQ migration (safe subset):** בוצעה מיגרציה מדורגת לשכבות polling/fetch בלבד בלי big-bang: `useChatUnreadMessages` עבר מ-`setInterval` ל-`useQuery` (`qk.chat.unread`), `useChatNotificationsFeed` עבר מ-`setInterval` ל-`useQuery` (`qk.notifications.all`) עם invalidate refresh API, ו-`Messages.tsx` עבר מ-`useState/useEffect` ל-`useQuery` (`qk.chat.conversations`) תוך שמירה על מיון/רנדרינג קיימים. שכבות WS הקריטיות (`useConversationMessages`, `useChatPopup`, `useChatWebSocket`, `processChatWebSocketMessage`) נשארו React state מקומי (לא RQ) — עם **`ChatListRow[]`** + optimistic send + reconciliation (ראו bullet “Chat outbound” למעלה). **תשומת לב:** מיגרציות **Stage 3b** מרכזיות (**`MyRides.tsx`**, **`MyBookings`**, חיפוש/בקשות נוסע ב־RQ) מתועדות ומסומנות ב־**[`docs/FRONTEND_UPGRADE_ROADMAP.md`](FRONTEND_UPGRADE_ROADMAP.md)**; שם גם הפערים (ניהול קבוצה, העלאות, `CreateRide`, צ’אט מלא וכו׳).
- **S.6 — Client-side request throttle (frontend):** נוסף token-bucket throttle ב-`frontend/src/api/throttle.ts` ומשולב כ-interceptor ראשון ב-`frontend/src/api/client.ts` כדי למתן bursts מהדפדפן ולייצב latency תחת פעולות UI מקבילות.
- **Bundle Budget B (tooling):** הוטמעו `rollup-plugin-visualizer`, `size-limit`, וחלוקת `manualChunks` ב-`vite.config.ts` (`react-vendor`, `query`, `firebase`, `sentry`, `i18n`, `forms`, `charts`) לצמצום drift בגודל bundle.
- **Stage 3b Part 6 — SearchRides targeted RQ migration:** `useSearchRides` הוסב למודל mutations נקודתי עבור `searchRidesApi`, `loadMoreResults`, ו-`saveSearchAlert`, תוך שמירה על state-machine קיים (AI flow, geolocation, `useOperationToken` race guards) וללא שינויי JSX. כך הושגה עקביות lifecycle ברשת בלי להרחיב blast-radius ב-wizard מורכב.
- **Stage 5 cleanup — MyRequests + Auth bootstrap effect:** `useMyRequests` הועבר ל-React Query (`qk.passengers.requests`, cancel mutation עם `setQueryData`, ו-`REQUEST_EXPIRED` cache patch), וחוזה ההחזרה נשמר תואם ל-`MyRequests.tsx`. בנוסף תוקן bug ב-`AuthContext` initial `useEffect` (dead mounted check) ע"י cancellable async pattern עם `cancelled` guard — שיפור יציבות boot ללא שינוי API חיצוני.
- **Premium UX end-to-end (frontend billing integration):** נוספו שכבות `api/billing.ts` + `features/billing` (React Query query/mutation עם `qk.billing.status` / `mk.billing.checkout`), קומפוננטת `PremiumBanner` בפרופיל (modes: active badge / upgrade CTA), ועמודי תשלום מוגנים `payment/success` + `payment/cancel`. עמוד הצלחה מבצע polling כל 2 שניות מול `/billing/status` עד `is_premium=true` או timeout של 30 שניות, עם תמיכה מלאה ב-RTL/i18n/tokens.
- **S.7 Asset hardening (frontend):** הוגדרו `loading`/`fetchpriority` ממוקדים לתמונות קריטיות מול רשימות, הוסף `preconnect` ל-S3 uploads, ו-i18n עבר למודל hybrid: `common`/`nav` inline bundled + lazy namespaces דרך `i18next-http-backend` מ-`/public/locales/*` (כולל preload ל-`he/auth` ו-`he/rides` לצמצום FOUE).
- **Web Vitals D — Sentry RUM (frontend):** ב-`PROD+DSN` הפרונט מפעיל `BrowserTracing` + `Replay` עם sampling שמרני (`0.05` session, `1.0` on-error), ודיווח `CLS/LCP/INP` דרך dynamic import של `web-vitals` כדי לשמור main bundle lean. נוסף גם `Sentry.setUser` lifecycle ב-`AuthContext` (bootstrap/login/google-login/logout) לשיוך מדויק של traces/replays למשתמש.
- **Frontend sourcemap upload (Sentry, production-safe):** `@sentry/vite-plugin` משולב ב-`vite.config.ts` בצורה מותנית (פועל רק ב-`production` ורק עם `SENTRY_AUTH_TOKEN`/`SENTRY_ORG`/`SENTRY_PROJECT`), כך ש-PR/local builds לא נכשלים בהיעדר secrets. ב-`frontend-ci` הסודות מוזרקים רק ל-`publish-image`; sourcemaps נמחקים מ-`dist` אחרי upload (`filesToDeleteAfterUpload`) כדי לא להיכנס ל-runtime image.
- **A11y Heading & Landmarks cleanup (frontend):** בוטלה כפילות `h1` גנרי ("LinkUp") ב-`Layout` וב-`PublicPageShell`; נשמר `<main>` יחיד לכל shell; נוספה utility גלובלית `.sr-only` ב-`index.css`; ודפים ללא כותרת ויזואלית קיבלו `h1` ספציפי + hook אחיד `usePageTitle` לעדכון `document.title` לפי route (`MyRides`, `MyRequests`, `MyBookings`, `SearchRides`, `Notifications`, `Messages`, `Groups`).
- **Loading states are full pages (a11y):** `PageLoading` ו-loading של `ProtectedRoute` הופכים ל-`<main aria-busy aria-live>` עם `<h1 sr-only>` (`common:loading` מתורגם), כך שגם פריימים של Suspense/auth-bootstrap עומדים בסטנדרט axe (`landmark-one-main`, `page-has-heading-one`, `region`) במעברי route עם lazy chunks.
- **Google Identity Services as module-level singleton (frontend):** `script` ו-`google.accounts.id.initialize()` הורמו ל-singleton אידמפוטנטי ב-`gisLoader.ts` (`loadScriptOnce`/`ensureGisInitialized`/`setGisCredentialHandler`); `useGoogleSignInScript` הפך ל-React adapter דק שלא מאפס דבר ב-cleanup — מבטל לחלוטין את אזהרת `initialize() called multiple times` תחת StrictMode וגם תחת re-renders שמשנים `onError` identity. נוסף DEV-only pre-flight log ב-`main.tsx` שמדפיס clientId+origin אפקטיביים והוראות מפורשות לאבחון 403 origin (Console allowlist / cache / scheme mismatch) במקום debugging מסתורי.
- **Dev-only ergonomics:** כפתור `ReactQueryDevtools` הוזז ל-`bottom-right` כדי למנוע חפיפה עם floating `ThemeToggle`/`LangToggle` ב-`bottom-left`.
- **PgBouncer (production-ready, Compose internal):** נוסף service ייעודי `pgbouncer` (transaction pooling) בין `backend`/workers לבין `db`, ללא חשיפת פורט חיצוני. שירותי runtime הסטנדארטיים **`backend`**, **`notification-worker`**, **`task-worker`**, **`ai-worker`** מחוברים דרך `POSTGRES_HOST=pgbouncer`; שירות legacy **`outbox-worker`** עם profile **`compat`** הוא alias לאותה תהליכית (**`notification-worker`**) — לא חלק מהסטאק ברירת־מחדל ב־Compose. **`migrate`** נשאר direct ל־**`db`** כדי למנוע friction ב-DDL/migrations. נוספה התאמת דרייבר ב-`session.py`: `connect_args={"statement_cache_size": 0}` עבור asyncpg + PgBouncer. בעקבות בעיות entrypoint ב-images ציבוריים, ה־service עבר ל־custom image (`infrastructure/pgbouncer/Dockerfile`) עם control מלא על `pgbouncer.ini`.
- **Redis HA with Sentinel (Compose-ready):** טופולוגיית Redis עברה ל-`redis-primary` + `redis-replica` + `redis-sentinel`. שירותי Python עובדים ב-`redis.asyncio.Sentinel` עם fallback ל-URL רגיל (dev), ו-`chat-ws` משתמש ב-`go-redis` `NewFailoverClient`. `REDIS_HOST=redis` נשמר כ-alias ל-master כדי לא לשבור קונבנציה קיימת, ו-`REDIS_SENTINEL_HOST` מפעיל את נתיב ה-HA.
- **Backend CD rollout on single EC2 (low-downtime):** **[`deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml)** מריץ לאחר CI מוצלח על `main` (אחד מארבעת ה-workflows) — SSH (`appleboy/ssh-action`), משיכת תמונות (`sha` עם fallback ל-`latest`), rollout ל-backend (`docker compose up -d --no-deps backend`) אחרי smokes פנימיים ל-`frontend` + `email-renderer`, ואז smoke-gate: `readyz`, `FIREBASE_CREDENTIALS_JSON`, ו-probes ציבוריים (`/livez` + `/config.js`). rollback אוטומטי לתג קודם; אם `docker pull` לתג הישן נכשל — **`backend:latest`**.
- **Rate limiting hardening (atomic + correct-by-threat):** הוחלף fixed-window לא אטומי (`INCR + EXPIRE`) בשני Lua scripts אטומיים: `sliding_window` ל-auth (ללא burst, anti-bruteforce) ו-`token_bucket` לצ'אט (burst-tolerant API throttling). החריגה `RateLimitExceeded` הועשרה ונוספו headers סטנדרטיים `X-RateLimit-Limit/Remaining/Reset` + `Retry-After`, יחד עם metrics ייעודיים (`rate_limit_rejected_total`, `rate_limit_redis_errors_total`, `rate_limit_evaluation_seconds`).
- **Billing (Stripe) — domain מלא עם hardening ברמת production:** דומיין `billing` (model/schema/crud/service/router), endpointים `checkout/status/payments/webhook`, אינטגרציה ל-`users` (**013**/**014**). **אידמפוטנטיות:** ברמת Stripe — **`stripe_event_id`** + **`stripe_payment_intent_id`**; ברמת checkout API — טבלה **`idempotency_keys`** + **`X-Idempotency-Key`** (רוויזיה **`015_billing_idem`**, ראו bullet “Billing — אידמפוטנטיות checkout” למעלה). **`PaymentStatus` enum**, מיפוי **`IntegrityError` → `PaymentAlreadyExistsError`**, אימות webhook **fail-closed**, Stripe דרך **`asyncio.to_thread`**, **`PaymentTransitionError`** למעברים אסורים, reconciler תפעולי + מדדים.
- **Circuit Breaker — Google Maps + Brevo (מחלקה משותפת + מדדים נפרדים):** המימוש הגנרי ב־**`backend/app/infrastructure/circuit_breaker.py`** (מוזן Prometheus `Gauge` לפי מופע). **גיאו:** **`backend/app/infrastructure/geo/circuit_breaker.py`** — singletons **`google_geocoding_cb`**, **`google_directions_cb`**, **`google_distance_matrix_cb`** על **`geo_circuit_breaker_state{name=…}`**. **`GeocodingService`** / **`GeoClient`** — **`allow_request()`** לפני HTTP; כש־**OPEN** — fail-fast (`None` / `[]`). **מייל:** **`backend/app/infrastructure/notifications/circuit_breaker.py`** — **`brevo_email_cb`** + **`brevo_circuit_breaker_state`**; **`EmailClient.send`** בודק מעגל לפני בלוק ה־Tenacity הפנימי (`_send_with_retry`); כש־**OPEN** — **`EmailProviderCircuitOpenError`** (503) בלי קריאה ל-Brevo; כשל לוגי אחרי ניסיונות retry — **`record_failure()`** פעם אחת. **`GET /api/v1/health`** כולל גם **`brevo_email`** תחת **`circuit_breakers`** — **אינפורמטיבי בלבד**; **`status`** נקבע רק מ־**database** / **redis** / **rabbitmq**. פירוט: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §20**, **`docs/architecture/API.md`** (Health), **`docs/architecture/NOTIFICATIONS.md`**.
- **Idempotency-Key ל־`POST …/passengers/request-ride-from-search` ול־`POST …/chat/conversations/{id}/messages`:** כותרת אופציונלית; Redis **`SET NX`** + fingerprint (SHA-256) על גוף קנוני; מטמון **רק 201**; **409 + Retry-After** בזמן עיבוד; **422** על `idempotency_key_mismatch`; שגיאת דומיין → מחיקת נעילה; **fail-open** בלי Redis. **בקאנד:** **`ride_join_idempotency.py`** (נסיעות) + **`message_idempotency.py`** (צ’אט), ראוטרים דקים. **פרונט:** **`useJoinRide`** + **`idempotencyKeyRef`** (נסיעות; מ־**`useSearchRides`**); **`sendMessage`** + **`useMessageThread`** / **`useChatPopup`** (מפתח יציב לניסיון, **`ChatListRow`**, **`applyInboundRealMessage`** / **`appendMessageDedupById`**, **`isChatIdempotencyKeyMismatch`**). פירוט: **§7ה**, **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §19** ו-**§25**, **`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` §2**.
- **JWT access-token revocation (Redis denylist):** כל access כולל **`jti`**; **`POST /auth/logout`** עם Bearer מוסיף `denylist:{jti}` עם TTL עד `exp`; HTTP dependencies וגם `get_current_user_ws` בודקים denylist בזמן handshake; **fail-open** אם Redis לא זמין. פירוט: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §18**, **`ARCHITECTURE.md`** (Key Patterns / Security), **סעיף 7ד** למטה.
- **Unified auth session teardown (frontend web):** [`tearDownSession({ reason })`](../frontend/src/context/AuthContext.tsx) מאחד **logout משתמש**, **כישלון bootstrap** (**`refreshUser`** / hydrate ראשוני), ו-**כישלון refresh** בפרונט. **`reason: user-action`** — `patchFcmToken(null)` + **`POST /auth/logout`** (בזמינות JWT תקף), לאחריו **`cleanupFCM`**, **`queryClient.clear()`**, **`Sentry.setUser(null)`** (PROD), **`clearTokens`**, **`isAuthenticated=false`**. **`session-expired`** / **`bootstrap-failed`** — רק ניקוי מקומי (אין PATCH/logout עם JWT מת). **[`client.ts`](../frontend/src/api/client.ts)** ב-**`refreshAccessToken`** — בעת **`!refresh_token`** או catch: **`clearTokens`** + **`auth:session-expired`** עם **guard reentrancy**; מסימון **`__sentryCaptured`** על 401 אחרי כשל רענון (defense-in-depth). [`queryClient.ts`](../frontend/src/api/queryClient.ts) — **`captureExceptionOnce`** מדלג על **401** בלבד (לא **403**). פירוט: **[FEATURE_DECISIONS.md](FEATURE_DECISIONS.md#auth-session-teardown)**, **ADR Frontend §21**.
- **Prometheus + Grafana monitoring:** backend חושף `GET /metrics` דרך `prometheus-fastapi-instrumentator`; ב-Compose נוספו שירותי `prometheus` ו-`grafana` תחת profile `monitoring`, עם provisioning מוכן + dashboard בסיסי ל-HTTP (`rate`, `p95`, `5xx`, `in_progress`).
- **Passenger match emails documented end-to-end:** Outbox publishes **`ride.created`**; `notification_tasks.handle_ride_created` runs `find_passengers_for_ride_notification`; per-match notification uses internal event **`ride.created_for_passengers`** (not a second Rabbit routing key). See §6.4 below and **`architecture/EVENTS.md`** (Ride section).
- **WebSocket notifications unified via `chat-ws`**: user refresh/domain events are pushed on the existing chat socket (`user:*:events`), reducing concurrent client WebSocket connections.
- **Outbox dispatch improved**: LISTEN/NOTIFY flow is now primary, with safe fallback behavior to avoid fixed-interval-only polling.
- **Worker split completed**: `notification-worker`, `task-worker`, `ai-worker` each has dedicated runtime responsibilities and K8s HPA policies.
- **DB pool caps per worker**: explicit `DB_POOL_SIZE` + `DB_MAX_OVERFLOW` were tuned per worker to keep total PostgreSQL connections in a safe range.
- **Redis reconnect resilience**: reconnect retry strategy now uses exponential backoff for long-lived pub/sub channels.
- **Frontend WebSocket reconnect — exponential backoff + jitter:** **[`computeReconnectDelayMs`](../frontend/src/utils/reconnectBackoff.ts)** — **3s** base, doubling, **30s** cap, **±20%** jitter — wired into **[`useChatWebSocket.ts`](../frontend/src/pages/MessageThread/useChatWebSocket.ts)** (chat-ws thread), **[`useReconnectingWebSocket.ts`](../frontend/src/hooks/useReconnectingWebSocket.ts)** (**`useUserEventStream`** על chat-ws + **`useRideWebSocket`** ל-FastAPI rides), **[`useReconnectingWebSocketState.ts`](../frontend/src/hooks/useReconnectingWebSocketState.ts)** (GPS); attempt counter resets on **`onopen`** and on new **`cid`** / **`reconnectKey`** (new effect). Reduces **thundering herd** after fleet-wide drops. See **[`FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff)**.
- **Google Maps resilience**: קריאות Geocoding / Directions / Distance Matrix עם **timeouts** ב־`httpx`; **Circuit Breaker** נפרד לכל API (מימוש משותף ב־`infrastructure/circuit_breaker.py`) למניעת storm כשספק הרשת/Google לא יציב; ב־reverse geocode — HTTP **429** מזוהה ככשלון במעגל ונזרקת **`InfrastructureError`** (`error_code` **`GEO_SERVICE_UNAVAILABLE`**) — פורמט אחיד ב־**`docs/ERRORS.md`**.
- **Geocode cache — הגנה מפני stampede:** בנתיב **`get_coordinates`** (`geocode_cache.py`) נוסף **`get_or_compute`** (`infrastructure/redis/cache_stampede.py`) — נעילת Redis פר־מפתח גיאוקוד, משימה ראשונה מפעילה את Google והכותבת ל־cache, עוקבים מחכים/קוראים ערך; **fail-open** כמו שאר הגיאוקוד. מדדי Prometheus: **`cache_lock_acquired_total`**, **`cache_stampede_avoided_total`**, **`cache_fail_open_total`**, בתוספת **`geo_cache_hits_total`** / **`geo_cache_misses_total`** למכסה הקריאות. טסט אינטגרציה: **`backend/tests/core_flows/test_geo_cache.py`** (cold key מתמזג עם mutex). פירוט: **`docs/FEATURE_DECISIONS.md#geocode-cache-stampede`**, **`docs/operations/MONITORING.md`**.
- **Chat reliability/UX**: on every **`chat-ws`** socket **`onopen`**, **`useChatWebSocket`** calls **`fetchMissedMessages(lastMessageIdRef.current ?? 0)`** (`GET …/messages?after=…`) so missed messages load even when there is no local **`message_id`** yet or when **`lastMessageIdRef`** is **`null`**; **`useConversationMessages`** keeps **`lastMessageIdRef`** as the max **`message_id`** over **confirmed** rows only (ignores **`pending`** tail); **`null`** when there are no confirmed messages. Reconnect gap fill uses **`fetchMissedGap`** ([`frontend/src/pages/MessageThread/fetchMissedGap.ts`](../frontend/src/pages/MessageThread/fetchMissedGap.ts)): **`after`** for the newest chunk, then **`before=next_cursor`** while **`has_more`** (aligned with **`docs/architecture/API.md`** cursor contract), capped at **50** HTTP pages (**~1500** messages), **two** retries per page, and **`shouldAbort`** when the hook’s **`conversation_id`** changes mid-run. **`fetchMissedMessages`** merges new server items by **`message_id`** and preserves any **pending** tail. Dedup for inbound reals: **`applyInboundRealMessage`** + **`appendMessageDedupById`**; **`limit: 30`** per HTTP page. Read receipts use a DB-level cursor (`last_read_message_id`) plus Redis **`message_read`** payloads including **`recipient_id`** so chat-ws routes live read-receipt updates to the sender. **WS reconnect pacing:** see **Frontend WebSocket reconnect** bullet above.
- **Chat POST idempotency:** optional **`Idempotency-Key`** on **`POST /chat/conversations/{id}/messages`** — same Redis primitives as passenger join (`message_idempotency.py`, key prefix `idempotency:chat_message:{user_id}:{key}`, fingerprint `conversation_id` + body); **[`sendMessage`](../frontend/src/api/chat.ts)** accepts an explicit key else generates UUID; **`useMessageThread`** / **`useChatPopup`** supply the stable-key lifecycle; list updates use **`applyInboundRealMessage`** / **`appendMessageDedupById`** (see **Latest architecture updates** — optimistic **`ChatListRow`**).
- **`useUserEventStream` framing:** inbound WS text is **`split('\\n')` per frame** before JSON parse — aligned with chat-ws **batched outbound frames** (`Conn` write pump). הוק מטפל ב־**`InvalidateEvent`** ואז ב־**`UserEvent`** (סדר קבוע).
- **FCM service worker:** background handling uses **`messaging.onBackgroundMessage`** reading **`payload.data`** (matches backend data-only pushes); redundant raw **`push`** listener removed to avoid duplicate or empty notifications.
- **Chat inbox N+1 fix + index hardening**: `list_my_conversations` הריצה `get_last_message` + `has_unread_messages` לכל שיחה בנפרד (~3N קריאות). הוחלפה ב-`get_inbox_aggregates` (`chat/crud.py`) — 3 aggregate queries + מיזוג בזיכרון, **4 קריאות קבועות**. נוסף `__table_args__` ב-`Message` model עם `Index("idx_messages_sender_id", "sender_id")` להתאמה ל-migration 012. פירוט: [FEATURE_DECISIONS.md — Chat inbox N+1](FEATURE_DECISIONS.md#chat-inbox-n1).
- **Task scheduler safety**: `task-worker` is fixed to a single replica to prevent duplicate scheduled task publishing.

---

## מפת פריטים: בסיס במאגר מול הרחבות (Portfolio / ראיון)

מסמך זה לא מייחס כל שורה ל”פיצ’ר בודד”; להלן **הבחנה מכוונת** בין יכולות שכבר היו **עמודי תווך בארכיטקטורה** לבין שכבות שהודגשו או הורחבו (במיוחד צ’אט בפרונט), ונקודות שמייצגות **סקייל / אמינות / אחידות חוזים** — מעבר למה שמצופה מג’וניור בלבד.

### כבר בשטח במאגר (דוגמאות מובילות)

| נושא | איפה / מה |
|------|-----------|
| **Idempotency-Key לשליחת הודעות** | בקאנד: Redis מלא, מודול ייעודי **`message_idempotency.py`**, חתימת גוף, `SET NX`, תגובות 409/422 — מיושר Stripe-style עם הפרונט (**ADR §25**, **Frontend ADR §2**). |
| **מיזוג רשימת הודעות (dedupe)** | פרונט: **`appendMessageDedupById`** ב־[`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts) — מקור אמת ל־`message_id` מול REST + WS. |
| **מחזור מפתח יציב לניסיון שליחה** | פרונט: **`consumeOrCreateKey` / `resetOutboundKey`** ב־[`outboundIdempotencyKey.ts`](../frontend/src/utils/outboundIdempotencyKey.ts). |
| **שגיאת אידמפוטנטיות בצ’אט** | פרונט: **`isChatIdempotencyKeyMismatch`** ב־[`apiError.ts`](../frontend/src/utils/apiError.ts) — ניתוב נקי ל־422 `idempotency_key_mismatch`. |
| **Stripe webhooks** | אימות חתימה **fail-closed** (`Stripe-Signature`), idempotency כפולה לרמת אירוע/תשלום — ראו bullet **Billing (Stripe)** ב־**Latest architecture updates**. |
| **אסטרטגיית ערוצי התראות** | בקאנד: **`NOTIFICATION_STRATEGY`** ב־[`backend/app/domain/notifications/config/mappings.py`](../backend/app/domain/notifications/config/mappings.py) + resolver/handler — מטריצת אירוע → ערוצים (מייל / FCM / in-app וכו’). |
| **שידורים בזמן אמת (נסיעות / GPS)** | **Redis Pub/Sub + WS ב-FastAPI** — טבלאות **`keys.py`** / **`broadcast`**, לא SaaS realtime חיצוני לניוד מיקום. |
| **Outbox → RabbitMQ** | **LISTEN/NOTIFY** ב-Postgres כנתיב ראשי לעידכון worker אחרי commit, עם fallback polling בטוח (**`notification-worker`**). |
| **פיקוח על קונסומרים ארוכי טווח** | **`run_supervised`** — restart מבוקר ל-workers עם backoff / `max_retries` (יחד עם שדרוגי RabbitMQ המתועדים למעלה). |
| **שני סוגי “ping” בצ’אט** | **אפליקציה:** הפרונט שולח JSON **`{"type":"ping"}`** כל **~30 שניות** (**`useChatWebSocket`**), כדי **לרענן נוכחות (TTL)** בצד **`chat-ws`** (handler `RefreshPresence` + pong). **פרוטוקול WebSocket:** **`chat-ws`** שולח **Ping frames** מהשרת בתדירות **`~54s`** (**`pingPeriod = (pongWait×9)/10`**, **`pongWait=60s`** ב־[`chat-ws/internal/hub/conn.go`](../chat-ws/internal/hub/conn.go)) — זיהוי חיבור מת / keep-alive שכבת Transport. זו **פרדיגמה כפולה מכוונת** (presence מול בריאות socket). |
| **מדידות / Firebase** | FCM ו־edge CSP (Firebase/Sentry/connect allowlists + `frame-src` ל־Stripe/Google) — **Latest updates**; אנליטיקס על Firebase/GTM כפי שנפרס בסביבות. |

### הרחבות / יישור פרונט שנוספו (צ’אט אופטימי ורשימה)

| נושא | איפה / מה |
|------|-----------|
| **טיפוסי רשימת צ’אט** | **`ChatListRow`** — [`types/chatList.ts`](../frontend/src/types/chatList.ts): **`confirmed`** / **`pending`**. |
| **מיזוג הודעה “אמיתית” + הסרת pending** | **`applyInboundRealMessage`**, **`removePendingByClientId`** — אותו [`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts); **`outboundPendingRef`** בתהליך ה-WS (**`processChatWebSocketMessage`**). |
| **גזירת מאגר למספרי הודעה / זנב אופטימי** | **`confirmedMessages`** + **`pendingTail`** ב־[`useConversationMessages.ts`](../frontend/src/pages/MessageThread/useConversationMessages.ts) — `lastMessageIdRef` רק על **confirmed**; שימור זנב **pending** אחרי backfill (**`fetchMissedMessages`**). |
| **אסטרטגיית reconnect ב־WebSocket (פרונט)** | מפרידה מ־**Redis reconnect backoff** בבקאנד (טבלת "כבר בשטח" למעלה). **`computeReconnectDelayMs`** ב־[`reconnectBackoff.ts`](../frontend/src/utils/reconnectBackoff.ts) — בסיס **3s**, כפול בכל כשל, תקרה **30s**, **±20% jitter**; hooks: **`useChatWebSocket`**, **`useReconnectingWebSocket`**, **`useReconnectingWebSocketState`**. **למה cap+jitter:** אחרי outage המוני — מונעים סנכרון של אלפי handshakes באותו רגע (**thundering herd**). |

**להצגה בראיון:** “לא עטפתי Idempotency בפרונט על עורק ריק — יש תאימות Redis מלא בבקאנד; בפרונט איחדתי dedupe, מפתח ניסיון, תרגום 422 למחזור מפתח, ואחר כך עטפתי רשימה בפרדיגמת union + reconcile מול WS/REST כדי שהמשתמש לא יחכה לרשת.”

---

## 0א. יציבות ופרודקשן — בעיה / החלטה / trade-off (סיכום)

סיכום ממוקד לראיון; פירוט טכני: **§7ד**, **§7ה**, **Latest updates**, **`ARCHITECTURE.md`**, ADR backend **§18–§26** (כולל JWT denylist, idempotency נסיעות/צ’אט/**billing checkout (§26)**, chat plaintext, rate limit, audit, וכו’).

### Idempotency-Key — `POST …/request-ride-from-search`

| | |
|--|--|
| **בעיה** | לחיצה כפולה במובייל או retry רשת יוצרות שתי הזמנות לאותה נסיעה. |
| **החלטה** | כותרת אופציונלית **`Idempotency-Key`** (UUID); Redis **`SET NX`** לנעילה פר-משתמש+מפתח; **SHA-256** על גוף קנוני — אי-התאמה → **422**; נשמרת רק תשובת **201** (מוסכמת Stripe); שגיאת דומיין → מחיקת נעילה; **fail-open** אם Redis למטה. בקאנד: **`ride_join_idempotency.py`**. פרונט: **`idempotencyKeyRef`** ב-**`useJoinRide`** (מ־**`useSearchRides`**). |
| **Trade-off** | בלי Redis אין dedup; זמינות מועדפת על idempotency קשיח ברגעי תקלה קצרים. |

### Circuit Breaker — Google Maps + Brevo (בקאנד)

| | |
|--|--|
| **בעיה** | timeout ארוך (למשל 15s) × בקשות מקבילות = סיכון ל-exhaustion של workers/threads כש-Google איטי; Brevo מושבת — Tenacity על ה-SDK ממשיך לנסות עד כיבוי התור. |
| **החלטה** | מחלקה משותפת + **גיאו:** שלושה **singletons** (**Geocoding**, **Directions**, **Distance Matrix**); **מייל:** **`brevo_email_cb`** לפני שליחה. **CLOSED → OPEN** (אחרי סף כשלונות) → **HALF_OPEN** (אחרי ~60s) → **CLOSED**; כש-**OPEN** — גיאו: ללא HTTP; Brevo: **`EMAIL_CIRCUIT_OPEN`** בלי קריאה לספק. מצב ב-**`GET /api/v1/health`** (`circuit_breakers`) **בלי** לשנות **`status`** הכללי; **fail-open** בתוך לוגיקת המעגל. |
| **Trade-off** | מצב לא משותף בין מופעים (restart מאפס); לא מיושם על S3 / Groq — שם async+boto3 או worker async. |

### Outbox — אירועים ל-RabbitMQ

| | |
|--|--|
| **בעיה** | publish ישיר לברוקר אחרי commit — crash או broker למטה = איבוד אירוע. |
| **החלטה** | כתיבה ל-**`outbox_events`** באותה טרנזקציה עם השינוי העסקי; worker מפרסם ל-RabbitMQ (LISTEN/NOTIFY + polling). |
| **Trade-off** | at-least-once + צורך ב-idempotency בצרכנים; latency קלה לעומת “fire-and-forget”. |

### PgBouncer — ממומש (Compose, internal-only)

| | |
|--|--|
| **בעיה** | עומסי burst/redeploy מייצרים fan-out של חיבורי DB, כולל סיכון ל-connection storms ו-memory pressure ב-Postgres. |
| **החלטה** | PgBouncer במצב `transaction` כשירות פנימי ב-Compose; runtime services מתחברים אליו, migration path נשאר direct ל-DB. |
| **מה שג׳וניור בד״כ מפספס** | (1) להשאיר `migrate` מחוץ ל-pooler. (2) לכבות `statement_cache_size` ל-asyncpg. (3) לא לחשוף `6432` החוצה בשלב ראשון. (4) להקטין pool אפליקטיבי כדי לא ליצור double-pooling לא מבוקר. |
| **מצב נוכחי** | פעיל ב-Compose: `docker-compose.yml`, `infrastructure/pgbouncer/pgbouncer.ini`, `backend/app/db/session.py`, smoke script ב-`scripts/ops/pgbouncer-smoke.sh`. |
| **ops hardening (חדש)** | `userlist.txt` לא נשמר ב-repo וגם לא נוצר על host/CI: PgBouncer יוצר אותו בתוך הקונטיינר בזמן startup מ־`userlist.txt.template` ו־`POSTGRES_*` + `PGBOUNCER_ADMIN_PASSWORD` (entrypoint), עם הרשאות פנימיות ובלי תלות UID/GID מול host. |

### Structured logging + correlation ID

| | |
|--|--|
| **בעיה** | לוגים לא מובנים וקשה לקשר שורות לאותה בקשה בפרודקשן. |
| **החלטה** | **structlog** (JSON prod / console dev); **`request_id_ctx`** + **`RequestIDMiddleware`** — **8 תווים**, כותרת **`X-Request-ID`**. |
| **Trade-off** | תלות ב-discipline של מפתחים להשתמש ב-logger המחובר ל-structlog לשדות עקביים. |

### JWT denylist (Redis)

| | |
|--|--|
| **בעיה** | אחרי logout ה-access JWT עדיין חתום ותקף עד `exp` אם אין revocation. |
| **החלטה** | **`jti`** בכל access; logout → **`SETEX denylist:{jti}`** עם TTL = זמן שנותר ל-`exp`; **`get_current_user`** / **`get_current_user_optional`** בודקים לפני המשך. **Fail-open** ב-`is_denied` אם Redis לא זמין. |
| **Trade-off** | חלון קצר שבו טוקן מבוטל עדיין מתקבל אם Redis למטה (fail-open); Refresh כבר נמחק ב-DB ב-logout — לא צריך denylist נפרד לו. |

---

## 1. מה בנינו (מוצר + יכולות)

| תחום | יכולות |
|------|--------|
| **נסיעות** | פרסום נסיעות, חיפוש (כולל גיאו / PostGIS), סטטוסים, שיוך לקבוצה / ציבורי |
| **נוסעים / התראות חיפוש** | חיפוש **`GET …/passenger/passengers/search-rides`** — ללא שורת DB; סינון זמן אופציונלי: **`departure_date`** (יום Jerusalem), **`departure_time`** (±2h), או **`departure_time`+`departure_time_to`**; **422** על שילוב לא חוקי. **שמירת בקשה + התראה** — **`POST …/passengers/`** עם `is_notification_active`, `group_id` אופציונלי; בעת יצירת נסיעה — worker מתאים בקשות פעילות (`find_passengers_for_ride_notification`) |
| **הזמנות** | בקשה, אישור/דחייה, race-safe (locks); **`POST …/request-ride-from-search`** — **Idempotency-Key** אופציונלי (Redis) נגד כפילות מלחיצה כפולה / retry |
| **צ’אט** | הודעות real-time, typing, נראות (online / last seen), **unread** (Redis→WS), קריאת שיחה; **DB-level read cursor** (`last_read_message_id`) ל-read receipts על כל ההודעות היוצאות; **Zod** על הודעה נכנסת ב־WS — `ChatMessageSchema` + מיפוי מפורש ל־`MessageResponse` ב־`processChatWebSocketMessage` |
| **קבוצות** | יצירה, **קוד הזמנה** Base62 (8 תווים, `secrets`), יצירה עם **`flush` + retry על `IntegrityError`** רק ל־duplicate על `invite_code`, **`commit`** אחד לקבוצה + חבר admin יוצר; אחרי כשלונות חוזרים — `LinkUpError` **`INVITE_CODE_GENERATION_FAILED`** (`app/domain/groups/crud.py`) |
| **AI** | סיכום שיחה: **`task-worker`** (idle timeout) → `handle_conversation_completion` (**Groq**) → **`chat_analysis`** + Outbox; **`ai-worker`** — מאזין אופציונלי ל־`chat:completion:*` ([`architecture/AI.md`](architecture/AI.md)); בנוסף **free-text** (`ai-parse-search`) ל-SearchRides / CreateRide |
| **התראות** | מייל (**Brevo**) עם רינדור HTML דרך **email-renderer (React Email)**, Push (**FCM** — מהשרת רק מפת `data` ב־FCM, בלי שדה `notification` של Firebase; בחזית **Toast קופץ + צליל**, ברקע התראת מערכת דרך SW), in-app |
| **משתמשים** | JWT (+ **`jti`**) + Refresh ב-DB; **`POST /auth/logout`** מנקה refresh ומבטל מיידית את ה-access הנוכחי דרך **Redis denylist**; **כניסה עם Google** (OAuth / `id_token`), אווטאר (S3 + worker; **קריאה:** CloudFront כשמוגדר או presigned); שדה **`is_admin`** לגישה ל־`/api/v1/admin/*` |
| **אדמין / תפעול** | ממשק ווב **`/admin`** (מודול `features/admin`): סטטיסטיקות, בריאות, משתמשים (הפעלה/הרשאת אדמין), נסיעות (ביטול), קבוצות, Outbox (requeue), lookup; **lazy routes**, מעטפת **דסקטופ** (ללא drawer מובייל), **`AdminRoute`** מינימלי (`is_admin` מ־AuthContext); אישור לפני מוטציות, toasts; בקאנד **`get_current_admin_user`** + לוג `[admin_audit]` — **`ADMIN_DASHBOARD.md`** |
| **מפות** | Google: **Geocoding**, **Directions**, **Distance Matrix**, **Maps JS**; geocoding הוא **Google-only** עם cache ב-Redis (24h); בבקאנד — **Circuit Breaker** נפרד לכל שלושת ה-APIs של Platform + מצב ב־**`/api/v1/health`** |
| **GPS בזמן אמת** | מיקום נהג לנוסעים, מיקום נוסעים לנהג (ערוצי Redis נפרדים + WS). **פרונט:** POST מותאם ב־throttle (~1.5s), `maximumAge: 0` לשידור, `useMapMarker` — יצירת marker פעם אחת ועדכון מיקום בלבד (בלי ריצוד), מפת Google. **Zod** על פריימי WS בכניסה — `frontend/src/types/wsEvents.ts`. פירוט: `docs/architecture/REALTIME.md`. |
| **תזכורות + אירועי משתמש ב-WS** | טבלת **`scheduled_notifications`** (Alembic 008) במקום דגל `reminder_sent` על rides/bookings; `ReminderScheduler` + handler. פרסום: **`publish_ride_event`** (broadcast/DB0); **`publish_user_event`** דרך **`redis_chat_pubsub`** / `REDIS_CHAT_URL` (DB1, כמו chat-ws) ל-`user:{id}:events`. **chat-ws** נרשם ל־**`user:*:events`** (בלי `chat:notification:*`); **פרונט:** `useUserEventStream` ב־`ChatContext` + מסכי My Rides & Bookings; טיפוסי **`Booking`** בפרונט ללא `reminder_sent` (יישור Phase 9). |
| **Workers / התראות** | RabbitMQ consumer — `notification_tasks`: שאילתות async (`select` + `execute`); **ביטול נסיעה** — התראה רק לבוקינג **PENDING** / **CONFIRMED** (לא כבר **CANCELLED**). |

---

## 2. סטאק טכנולוגי

| שכבה | טכנולוגיה |
|------|-----------|
| API | **Python 3**, **FastAPI**, async SQLAlchemy, **Alembic** |
| Real-time chat WS | **Go** — שרת WebSocket ייעודי (`chat-ws`) |
| Frontend | **React**, **Vite**, TypeScript, **Zod** (אימות JSON מ-WebSocket בפרונט); **i18next** (he/en); **`utils/date.ts`** + **`getLocale()`**; **`utils/i18nError.ts`** (`apiErr`) ל-fallbacks מתורגמים ב־hooks |
| DB | **PostgreSQL 15** + **PostGIS** (גיאומטריה, מרחקים) |
| Cache / Pub-Sub | **Redis** — **הפרדה ל-DB 0 (API, denylist ל-JWT, idempotency keys, cache, rate limit) ו-DB 1 (צ’אט + completion)** |
| Broker | **RabbitMQ** — תורים לאירועים ומשימות כבדות |
| אחסון / מדיה | **S3** (העלאות — presigned PUT); **קריאה ציבורית** — כשמוגדר **`CLOUDFRONT_DOMAIN`**, URLs יציבים דרך **Amazon CloudFront** (מקור: אותו bucket); בלי CDN — presigned GET ל-S3. אווטאר משתמש: prefix **גרסתי immutable** `avatars/{user_id}/v{version}/` — מחיקת גרסה קודמת ב-S3 רק **אחרי** commit ל-`users.avatar_key` (עם ניקוי orphan אם ה-commit נכשל). |
| פריסה | **Docker Compose**; **Kubernetes** (למשל `k8s/chat-ws`) |
| AI (צ’אט) | **Groq** — מודל Llama (למשל `llama-3.3-70b-versatile`) לניתוח שיחה |
| מייל | **Brevo** (API transactional) + **email-renderer** (Node.js/Express + React Email) |
| Push | **FCM** — `fcm_token` ב-DB; שליחה דרך Firebase Admin עם **`data` בלבד** (ללא בלוק `notification` של FCM); הצגה בידי האפליקציה: ברקע SW על `push`; בחזית **Toast + צליל** (`onMessage` + `payload.data`) |
| כניסה Google | **Google Sign-In** — אימות `id_token` ב-backend; client ID משותף FE/BE (`backend/docs/GOOGLE_OAUTH.md`) |

---

## 2ב. שגיאות API אחידות (Backend + Frontend + chat-ws)

| שכבה | מה ממומש |
|------|----------|
| **FastAPI** | `LinkUpError` ותתי־מחלקות לפי דומיין ב־`app/core/exceptions/`; handlers ב־`main.py` ל־validation (422), `IntegrityError` / `SQLAlchemyError`, ו־`LinkUpError`. תגובה: `detail` עם `error_code`, `message`, `trace_id`, `payload` אופציונלי — **`docs/ERRORS.md`**. |
| **Frontend** | `useErrorHandler` (axios), `ChatErrorBoundary`; טיפוסים לפורמט שגיאה. |
| **chat-ws (Go)** | לוגים מובנים עם **`slog`**; ל-HTTP (למשל PATCH last-seen) תגובות JSON עקביות; סגירת WebSocket עם קודים מתועדים היכן שרלוונטי — פירוט ב־**`docs/ERRORS.md`**. |

### כל סוגי ה-API שקשורים למפות / מיקום (מלא)

**מפתח אחד לרוב Google Maps Platform:** `GOOGLE_MAPS_API_KEY` — מופעל ב-Console עבור כל ה-APIs הרלוונטיים (Geocoding, Directions, Distance Matrix, Maps JavaScript).

| # | API / שירות | איפה בקוד | תפקיד |
|---|-------------|-----------|--------|
| 1 | **Google Maps Geocoding API** (`/maps/api/geocode/json`) | `GeocodingService` — כתובת→קואורדינטות ו-**reverse** (קואורדינטות→כתובת) | זרימות דרך `domain/geo` (למשל מיקום נוכחי, עיבוד כתובות); טיפול ב-429 וכו’. עטוף ב־**`google_geocoding_cb`**. |
| 2 | **Google Directions API** (`/maps/api/directions/json`) | `infrastructure/geo/client.py` | עד **3 מסלולים** חלופיים, `language=he`, polyline לתצוגה. עטוף ב־**`google_directions_cb`**. |
| 3 | **Google Distance Matrix API** (`/maps/api/distancematrix/json`) | אותו `GeoClient` | זמן נסיעה ומרחק מוצא–יעד (מיושר למסלולים). עטוף ב־**`google_distance_matrix_cb`**. |
| 4 | **Google Maps JavaScript API** (`maps/api/js?key=…`) | פרונט: `loadGoogleMaps`, מודלי מפה חיים / מסלול | מפת **Google** באפליקציה; המפתח מגיע מ-**`GET /api/v1/geo/maps-key`** (או `VITE_GOOGLE_MAPS_API_KEY`). |
| 5 | **Geocode cache (Redis, 24h) + stampede coalescing** | [`geocode_cache.py`](../backend/app/infrastructure/geo/geocode_cache.py) + [`cache_stampede.py`](../backend/app/infrastructure/redis/cache_stampede.py) + `GeocodingService` | TTL 24h, **fail-open**; **cold miss** או פרץ של בקשות מקבילות על אותו מפתח — **mutex Redis** מאחד קריאה אחת ל-Google; מטריקות ב־**`MONITORING.md`** |
| 6 | **OSRM** (דוגמה ציבורית) | קבוע `OSRM_URL` ב-`GeoClient` | **לא** בשימוש בזרימת `fetch_raw_routes` הנוכחית (שם רק Google); נשאר כתשתית אפשרית. |

**כניסה עם Google (לא מפות):** **OAuth / Identity** — `GOOGLE_CLIENT_ID`, ראה `backend/docs/GOOGLE_OAUTH.md`.

**לסיכום לראיון:** “במפות יש לי **ארבעה APIs של Google Platform** — Geocoding (כולל reverse), Directions, Distance Matrix, ו-JavaScript למפה בדפדפן; geocoding הוא **Google-only** עם cache ב־Redis (24h), **וכשמגיע עומס מקביל על אותה כתובת קר מפעילים coalescing דרך נעילת Redis כדי לא לרוקן quota**; מפתח Maps נפרד מ-OAuth של Login.”

---

## 2א. Workers: מה רץ כל הזמן ומה לפי זמן

תהליכי ה-worker פוצלו לפי אחריות: **`notification-worker`**, **`task-worker`**, **`ai-worker`**.

### רצים כל הזמן (כל עוד ה-worker חי)

| רכיב | תפקיד |
|------|--------|
| **`notification-worker`** | Outbox LISTEN/NOTIFY + fallback polling, consumer ל-`notifications_queue` (מייל+FCM+user refresh). |
| **`task-worker`** | consumers ל-`avatar_upload_queue` ו-`scheduled_tasks_queue`, plus scheduled publisher loop כל ~**60 שניות**; משימות scheduled כוללות **chat idle timeout** → `handle_conversation_completion` (**Groq** → `chat_analysis` + Outbox). |
| **`ai-worker`** | מאזין **אופציונלי** ל-`chat:completion:*` (Redis DB הצ’אט); אם מתקבל payload — אותו ניתוח; **אין ב-backend פרסום Python מאומת** לערוץ — ראו [`architecture/AI.md`](architecture/AI.md). |

### משימות לפי מרווח זמן (מתוזמנות דרך התור)

ה-publisher שולח ל-RabbitMQ לפי מרווחים (הערכים בקוד):

| משימה | מרווח טיפוסי |
|--------|----------------|
| תזכורות (reminders) | כל **5 דקות** (300s) |
| תחזוקה (maintenance) | כל **25 דקות** (1500s) |
| chat timeout | כל **שעה** (3600s) |
| סריקת דלק (fuel / EIA) | **יומי** (86400s) |

כך נשמרת הפרדה: **מתזמן קל** שרק דוחף אירועים, ו-**worker אחיד** שמבצע — קל להרחבה ולמעקב.

---

## 3. ארכיטקטורה לסקייל

- **Backend stateless** — כל הלוגיקה העסקית ב-FastAPI; אפשר להרחיב replicas; **Redis משותף** ל־**JWT denylist** + **Idempotency-Key** (מטמון POST) בין מופעים; WebSocket לצ’אט **לא** על אותו process (מפורק ל-Go).
- **הפרדת שירותים**: REST + DB ב-Python; **מאות אלפי חיבורי WS** יכולים לרוץ על מופעי `chat-ws` נפרדים מאחורי load balancer (sticky או shared Redis).
- **Redis Pub/Sub** — publish מה-API, subscribe ב-Go; לא דוחפים הודעות דרך Python WS.
- **Connection pool** ל-Postgres: `pool_size`, `max_overflow`, **`pool_timeout`**, **`pool_recycle`**, `pool_pre_ping` — מוגדרים מ-**`settings` / `.env`** (`DB_POOL_*`); מפחית חיבורים מתים והמתנה אינסופית לחיבור פנוי.
- **Cursor pagination** לחיפוש נסיעות ולהודעות צ’אט — עמידות בנתונים גדולים לעומת offset גדול.

---

## 4. Real-time — צ’אט (WebSocket + Redis)

### זרימה כללית

1. שליחת הודעה: **POST** ל-API → שמירה ב-DB → **PUBLISH** ל-`chat:conversation:{id}`.
2. **chat-ws (Go)** מאזין ל-pattern, מעביר ללקוח לפי נמען.

### פיצ’רים על החיבור

| פיצ’ר | מימוש (קצר) |
|--------|----------------|
| **Typing** | הלקוח שולח `typing_start` / `typing_stop` → Redis `chat:typing:*` → Go מעביר לצד השני. |
| **Online (presence)** | בחיבור: `SET presence:{user_id}` עם TTL (~60s). **Ping** מהלקוח מרענן TTL. |
| **Connect** | **`PUBLISH user:online`** → WS `user_online` לכל הלקוחות (שותף רואה “מחובר” מיד). |
| **Disconnect** | **מחיקת** `presence` + **`PUBLISH user:offline`** → WS `user_offline`; **debounce** ל-last-seen ב-DB. **Redis:** שרת אחד, **DB0** backend / **DB1** צ’אט+presence. |
| **Last seen (debounce)** | מפתחות Redis: `debounce:last_seen:{user}`, **`last_seen:hold:{user}`** (ערך **timestamp**, לא JWT), **`last_seen:token:{user}`** (Bearer; מחיקה רק אחרי PATCH מוצלח). Worker ב-Go: אם debounce פג → **PATCH** `users/me/last-seen` → עדכון **`users.last_active_at`** (**נפרד מ־`last_login`**; שליחת הודעה בצ’אט מעדכנת גם כן). **חיבור מחדש** מנקה את כל המפתחות. |
| **UI — last seen** | בפרונט: **`formatChatLastSeen`** מגן מפני **Invalid Date**. |
| **אימות** | אותו **JWT** כמו ה-API (`SECRET_KEY` משותף). |

פירוט ערוצים ומפתחות: `architecture/REALTIME.md`. **Presence ב-UI**: טעינה חד־פעמית של `GET` ל-**chat-ws** `/presence/{id}` + עדכון בזמן אמת מ-WS `user_online` / `user_offline`.

### מקליד · מחובר · התנתקות — איך זה עובד (להצגה בראיון)

| מה רואים במוצר | מה קורה בטכנולוגיה |
|----------------|---------------------|
| **משתמש מקליד** | הפרונט שולח ב-WebSocket `typing_start` (בדרך כלל עם throttle). כשמפסיקים — `typing_stop` (למשל אחרי שליחה או blur). **chat-ws** מפרסם ל-Redis `chat:typing:*` (עם הגבלה פר־חיבור מהצד הנכנס; **`ping`** ללא הגבלה מסוג זה) והמנוי מעביר לאותו conversation לצד השני — **בלי** לגעת ב-DB. זה **אפhemeral** ומתאים למאות אלפי אירועים קצרים. |
| **משתמש מחובר** | בפתיחת WS: Go שם `presence:{user_id}` ומפרסם **`user:online`** → **`user_online`** ב-WS. בכניסה לשיחה: **קריאה אחת** ל-`GET /presence/{partner_id}` לטעינת מצב ראשוני. |
| **התנתקות (Disconnect)** | Go **מפרסם** `user:offline` → **`user_offline`** ב-WebSocket. במקביל debounce ל-PATCH last-seen (`last_active_at`). |

---

## 5. Real-time נוסף (לא צ’אט)

- **עדכוני נסיעה**: WS ב-FastAPI + Redis Pub/Sub; **מקור אמת לשמות ערוצים** — `app/infrastructure/redis/keys.py` (`get_ride_channel` וכו'). **נקודת כניסה אחת לשידור אירועי נסיעה** — `publish_ride_event` ב־[`app/infrastructure/redis/publisher.py`](../backend/app/infrastructure/redis/publisher.py) (אירועים כמו `RIDE_STARTED` / `RIDE_ENDED` / `RIDE_CANCELLED`). חיבור ל־**`/api/v1/rides/ws/{ride_id}`** דורש `?token=JWT` (כמו שאר ה-WS ב-backend).
- **מיקום נהג / נוסעים**: ערוצים נפרדים (`booking_*`, `ride_*:passenger_locations`) + WS ייעודיים — הפרדת עומס ולוגיקה.
- **פרונט (WS)**: **`useRideWebSocket`** — hook גנרי עם reconnect; **`useDriverLocation`** / **`usePassengerLocations`** — reconnect אוטומטי אחרי ניתוק; **`MyRides.tsx`** — מאזינים לערוץ נסיעה עם אותו חוזה JSON. כשנהג לוחץ **התחל נסיעה**, הנוסע רואה מיד את אפשרות **שתף מיקום** (רענון רשימה דרך אירועי סטטוס).
- **אימות JSON (Zod)**: סכימות מרוכזות ב-**`frontend/src/types/wsEvents.ts`** — `RideEventSchema`, `DriverLocationEventSchema`, `PassengerLocationEventSchema`, **`InvalidateEventSchema`** (רענון באדג'ים/`resource`), **`ChatPresenceEventSchema`** (כולל `unread_count` לערוץ צ'אט), **`UserEventSchema`** לפריימים מ־`user:{id}:events`. ב-`onmessage` משתמשים ב-**`safeParse`**; פריימים לא צפויים → דילוג. שימוש ב-**`useRideWebSocket`**, **`useDriverLocation`**, **`usePassengerLocations`**, **`MyRides`**, **`processChatWebSocketMessage`**, **`useUserEventStream`**.

---

## 6. סינכרוני מול אסינכרוני + RabbitMQ

במערכת משולבים שני עולמות: **הלקוח מחכה לתשובה (סינכרוני לחוויית משתמש)** מול **עבודה שמתבצעת אחרי שהבקשה נסגרה (אסינכרוני)** — כדי לא לחסום את ה-API ולא לאבד משימות.

### 6.1 מה סינכרוני ומה אסינכרוני (דוגמאות)

| סינכרוני (הלקוח מקבל תשובה מיד / בזמן הבקשה) | אסינכרוני (ממשיכים ברקע; הלקוח לא מחכה) |
|-----------------------------------------------|------------------------------------------|
| **REST**: login, שליחת הודעת צ’אט (POST), אישור הזמנה, חיפוש נסיעות | **מייל / Push** אחרי אירוע עסקי — דרך Outbox → RabbitMQ → consumer |
| **תשובת 200** אחרי commit ל-DB (והפעלת publish ל-Redis לצ’אט) | **עיבוד אווטאר** (S3 resize) — נכנס לתור, ה-API רק מחזיר “התקבל” |
| **GET /presence** ב-chat-ws (online + last_seen מ-DB דרך backend) | **ניתוח AI לשיחה** — עיקרית **`task-worker`** (timeout); מאזין **`ai-worker`** ל־`chat:completion:*` (אופציונלי) — [`architecture/AI.md`](architecture/AI.md) |
| **PATCH last-seen** — נקרא מה-worker ב-Go אחרי disconnect (לא מהדפדפן של המשתמש המנותק) | **משימות מתוזמנות** (תזכורות, chat timeout, וכו’) — RabbitMQ `scheduled` |
| | **Redis Pub/Sub** — publish לא “מחכה” למנויים; מי שלא מחובר לא מקבל — זה push חד-כיווני |

**עקרון**: דברים שחייבים **עקביות עם DB** (למשל “שמרנו הזמנה”) נשארים בטרנזקציה. דברים ש**יכולים להיכשל זמנית** (מייל, חיצוני, כבד) — **מחוץ** לטרנזקציית ה-HTTP, דרך תורים.

### 6.2 RabbitMQ — תפקיד במערכת

- **לא** כל בקשה עוברת ב-RabbitMQ. ה-API מדבר ישירות עם Postgres / Redis.
- **`notification-worker`** (פונקציית **`run_outbox_worker`**) קורא `outbox_events` (PENDING) ו**מפרסם** ל-RabbitMQ לפי routing (user / ride / booking / tasks / scheduled).
- **Consumers** נפרדים: למשל `notifications_queue` (מייל Brevo + Firebase), `avatar_upload_queue`, `scheduled_tasks_queue`.
- **DLQ:** Retry failures are handled broker-side via `retry_exchange` + `<queue>.retry` (`x-message-ttl`) with attempts counted from `x-death`; terminal failures are routed to per-queue `.dlq` — **not lost**. `scheduled_tasks_queue` remains **no-DLQ** by design (failures are logged and acked). פירוט: [`architecture/EVENTS.md`](architecture/EVENTS.md) (Retry / Dead Letter Queues).
- **יתרון לסקייל**: אפשר להוסיף workers שמושכים מהתור בלי להעמיס על ה-API; **backpressure** — אם שליחת מייל איטית, התור גודל והמערכת לא קורסת.

### 6.3 Outbox — החיבור בין סינכרון לאסינכרון

- באותה **טרנזקציה** עם עדכון עסקי נכתב שורה ל-`outbox_events`.
- אחרי commit, תהליך נפרד מפרסם ל-RabbitMQ. כך **לא** יוצא מצב: “הזמנה נשמרה אבל האירוע לתור אבד”.
- פירוט exchanges/queues: `architecture/EVENTS.md`.

### 6.4 End-to-end: נסיעה חדשה שמפרסם נהג → מייל לנוסעים מתאימים

רצף מקור אמת בקוד (להבדיל בין **routing key ב-Rabbit** לבין **שם אירוע ההתראה הפנימי**):

1. **`POST` יצירת נסיעה** — [`RideService._persist_ride_and_publish_event`](../backend/app/domain/rides/service.py) כותב `ride` ו-Outbox עם שם האירוע **`ride.created`**.
2. **`notification-worker`** — `run_outbox_worker` מפרסם ל-exchange `ride`; consumer על `notifications_queue` מקבל **`routing_key=ride.created`**.
3. **[`handle_ride_created`](../backend/app/workers/tasks/notification_tasks.py)** — טוען `Ride`, מריץ [`find_passengers_for_ride_notification`](../backend/app/domain/passengers/crud.py); לכל `PassengerRequest` — `notification_handler` עם **`ride.created_for_passengers`** (מחרוזת ה-enum, לא Outbox נפרד).
4. **אין** יצירת הזמנה אוטומטית; המייל מזמין את הנוסע לפתוח את האפליקציה / לחפש שוב.

**תנאי תפעול:** Worker + RabbitMQ + Postgres; לנסיעה חייבים `departure_time`, `route_coords`, `destination_geom`; בקשת נוסע חייבת `is_notification_active`, `requested_departure_time` בעתיד, והתאמה גיאוגרפית ולוחית (כולל `group_id` — נסיעה ללא קבוצה מתאימה רק ל-`passenger_requests` עם `group_id IS NULL`). פירוט טבלאות אירועים מתוקן: **`docs/architecture/EVENTS.md`**.

---

## 7. דפוסים ו”טריקים” ברמת קוד

| דפוס | למה |
|------|-----|
| **Circuit Breaker (Google Maps + Brevo)** | מחלקה משותפת ב־`infrastructure/circuit_breaker.py` עם `Gauge` מוזרק. גיאו: שלושה singletons (Geocoding / Directions / Distance Matrix). מייל: `brevo_email_cb` — מעגל לפני שליחה ל-Brevo; Tenacity על `_send_with_retry` פנימית; `EMAIL_CIRCUIT_OPEN` כשהמעגל OPEN. מצב ב־`/api/v1/health` (**לא** משפיע על readiness). ADR **§20**. |
| **DDD** | דומיינים מבודדים (rides, bookings, chat, …) — קל להרחבה וטסטים. |
| **Pessimistic locking** | אישור/ביטול הזמנה תחת `SELECT FOR UPDATE` — מונע race ו”כפל” לוגיקה תחרותית על אותה נסיעה. |
| **Async SQLAlchemy 2.0 migration** | זרימות ליבה בדומיינים passengers/bookings/rides עברו ל-`AsyncSession` + `select/execute`; פעולות sync נשמרו רק למקטעים שדורשים locking/transactional guarantees. |
| **Chat inbox — aggregate query (N+1 fix)** | `get_inbox_aggregates` (`chat/crud.py`) — 3 שאילתות `func.max` מאוגדות לכלל השיחות במקום `get_last_message` + `has_unread_messages` per-row; מ-~3N ל-4 קריאות קבועות ללא תלות בגודל ה-inbox. פירוט: [FEATURE_DECISIONS.md — Chat inbox N+1](FEATURE_DECISIONS.md#chat-inbox-n1). |
| **JWT קצר + Refresh ב-DB + `jti` + Redis denylist** | אבטחה; refresh נמחק ב-logout; access הנוכחי נחסם מיידית עד `exp` (TTL על `denylist:{jti}`). |
| **Idempotency-Key (Redis, `SET NX`)** | `POST …/request-ride-from-search` — מניע duplicate booking; מטמון **201** בלבד; **§7ה**. |
| **Billing checkout idempotency (Postgres)** | **`X-Idempotency-Key`** על **`POST /billing/checkout`** — טבלה **`idempotency_keys`**, **`IdempotencyMismatchError`**; reconciler + **`validate_transition`** — ראו **Latest updates** (Billing) ו-[FEATURE_DECISIONS](FEATURE_DECISIONS.md#billing-checkout-db-idempotency-reconciler). |
| **Rate limiting (Redis)** | על **register**, **login / refresh** ונקודות auth נוספות — מונה ב-Redis, חלון זמן + מקסימום בקשות ל-IP — מגביל הרשמה/כניסה אגרסיבית; בצ'אט יש rate limit פר-משתמש על `POST /chat/conversations/{conversation_id}/messages` (30 הודעות/דקה, fail-open אם Redis לא זמין). |
| **API docs hardening** | `/docs`, `/redoc`, `/openapi.json` נשלטים ע"י `API_DOCS_ENABLED`; ברירת מחדל `False` כדי להשבית חשיפת סכימת API בפרודקשן, והפעלה רק בסביבות פנימיות (dev/staging). |
| **מניעת username enumeration (OWASP)** | לוגין: **אותה** `InvalidCredentialsError` (401) לאימייל שלא קיים ולסיסמה שגויה — לא חושפים אם המשתמש רשום. |
| **bcrypt ב-thread pool** | `get_password_hash` / `verify_password` — **async** עם `asyncio.get_running_loop().run_in_executor` — לא חוסמים את לולאת ה-ASGI תחת עומס סיסמאות. |
| **Request ID** | `X-Request-ID` — מעקב בין לוגים לבקשה. |
| **JSON logging בפרודקשן** | **python-json-logger** v3+ (`pythonjsonlogger.json`); ingestion ל-ELK / CloudWatch בעתיד. |
| **Uvicorn + מספר workers** (`UVICORN_WORKERS` ב־`backend/.env`; `entrypoint.sh` בדוקר; `.env.example` מציין 4) | ניצול מספר cores ל-API. |
| **Redis DB נפרד לצ’אט** | בידוד עומס pub/sub ומפתחות צ’אט מ-cache הכללי של ה-API. |

### 7ב. Defensive Programming (תכנות הגנתי) — כן, ממומש בפרויקט

**Defensive programming** = להניח שתקלות, קלט שגי ותחרות קיימים; להגן על המערכת במקום “לקרוס בשקט”. ב-LinkUp זה בא לידי ביטוי בין היתר ב:

| שכבה | דוגמאות מהקוד |
|------|----------------|
| **עסקי / DB** | בדיקות `if not ride` / בעלות לפני פעולה; **pessimistic lock** על הזמנות; **Outbox** כדי שלא יאבדו אירועים אחרי commit. |
| **רשת / חיצוני** | **Timeouts** ל-Google Geocoding / Directions / Distance Matrix; **Circuit Breaker** נפרד לכל API Maps + מעגל ל-Brevo ב-`EmailClient` (fail-fast כשהמעגל OPEN); טיפול ב-**429** ב-reverse geocode עם הודעת דומיין; debounce **last-seen** + ביטול ב-reconnect — לא מציפים DB ולא מעדכנים “offline” בטעות. |
| **תשתית** | **`pool_pre_ping`**, **`pool_timeout`**, **`pool_recycle`** — מאגר DB עמיד יותר; **rate limit** על register + login/refresh; **FCM** — טוקן לא תקף: דילוג בשליחה אם אין טוקן; איפוס **`fcm_token`** ב-DB כש-Firebase מחזיר רישום לא תקף (**`PushProvider`** + session מה-handler). |
| **chat-ws (Go)** | `if redisClient == nil` לפני פעולות; **select default** על ערוץ Send; לקוחות Redis נפרדים ל-`user:offline` ול-`user:online` שלא ייתקעו עם `PSubscribe` של הצ’אט; **`SetReadLimit(2048)`** + דילול **`typing_*`** פר־חיבור (`x/time/rate`; **`ping`** פטור). |
| **API / HTTP** | **LinkUpError** + handlers מרוכזים; **CORS** גם על תגובות שגיאה; אימות JWT לפני WS ולפני `/presence`. |
| **פרונט** | `try/catch` על טעינת presence / WS; **פיצול הודעות WS לפי `\n`**; `user_online` / `user_offline` עם **ref** ל-partner. |
| **איכות** | טסטים ל-**JWT** (פג תוקף, חתימה שגויה) — מגנים על נקודות כשל אימות. |

זה לא “פריימוורק” בשם אלא **שילוב דפוסים**; בריאיון אפשר לומר: *“יש אצלי defensive layers — locks, outbox, timeouts, debounce, ו-validation לפני שינויי מצב.”*

---

## 7א. אבטחה (סיכום להצגה)

| נושא | מימוש |
|------|--------|
| סיסמאות | Hash (**bcrypt** / passlib); חישוב ואימות **אסינכרוניים** דרך **`run_in_executor`** (לא חוסמים event loop). |
| OTP (אימות מייל וכו’) | יצירה עם **`secrets`**; השוואה עם **`hmac.compare_digest`**; מונה ניסיונות ב-Redis; איפוס מונה בעת **`create_verification_event`** (קוד חדש). |
| עומס על Auth | **Rate limit** (Redis) על נקודות רגישות — כולל **`POST /register`**, login, refresh וכו’. |
| User enumeration | **OWASP:** בלוגין — `InvalidCredentialsError` זהה לאימייל לא קיים **ול** סיסמה שגויה (אין הבחנה בתגובה). |
| סשן | JWT (HS256), `SECRET_KEY` חובה בפרודקשן; **`jti`** ל-access; denylist ב-Redis אחרי logout; אותו סוד ל-chat-ws לאימות WS. |
| Google | אימות טוקן מול Google; לא מחליפים לבד ללא אימות שרת. |
| HTTP | CORS מוגדר (`CORS_ORIGINS` / `FRONTEND_URL`); אופציה לכפיית HTTPS מאחורי proxy. |

### 7ג. הרשמה והתחברות תחת עומס גבוה (מאות / אלפי בקשות מקבילות)

הציר **auth** תוכנן כך שמקביליות רבה לא “תקעה” את השרת ולא תיצור race על משאבי DB/CPU:

| שכבה | מימוש | קשר לסינכרון / אסינכרון |
|------|--------|-------------------------|
| **Event loop (FastAPI / ASGI)** | **bcrypt** (hash / verify) רץ ב־**`asyncio.run_in_executor`** — ממשק async לקוד, עבודת CPU ב-thread pool. | **אסינכרוני** מבחינת הלולאה: אלפי בקשות לא ממתינות אחת לשנייה על חישוב סיסמה באותו thread. |
| **מאגר חיבורי DB** | **`DB_POOL_*`** — `pool_size`, `max_overflow`, `pool_timeout`, `pool_recycle`, **`pool_pre_ping`**. | תומך בהרבה **sessions אסינכרוניות** במקביל בלי לייבש את ה-pool או להחזיק חיבורים מתים. |
| **Redis** | **Rate limit** לפי IP על **`/register`**, login, refresh (וגם) — לפני עבודה כבדה. | בדיקה **מהירה**; מגנה על ה-API מפני ספאם ומפחית עומס מיותר על DB+bcrypt. |
| **טרנזקציה מול צדדיות** | **Register:** יצירת משתמש + שורות **Outbox** (`user.registered`, `auth.email_verification`) באותה טרנזקציה; מייל נשלח דרך **worker / RabbitMQ** אחרי ה-commit. | **סינכרון:** שלמות נתונים ב-DB. **אסינכרון:** שליחת אימייל והמשך pipeline לא חוסמים את זמן התגובה הקריטי של הרישום. |
| **הולידציית טלפון** | **`phonenumbers==8.13.48`** (נעול) — עקביות מול מטא־דאטה ישראלית. | מפחית כשלים אקראיים ב-validation תחת עומס (גרסאות 9.x שינו התנהגות). |
| **בדיקת עומס (k6)** | מקור אמת: **`backend/k6/scripts/load_test_auth.js`** (register + login לכל איטרציה); **`backend/load_test.js`** — wrapper תואם לאחור. | מאמת end-to-end את השילוב: API, DB pool, Redis (rate limit), validation. **דוגמה למדידה לוקאלית:** 10 VU למשך 30s, ~150 איטרציות, **שיעור שגיאות HTTP 0%**, p95 register ~413ms / login ~363ms (תלוי חומרה וסביבה). שאר שכבות: **`backend/k6/scripts/`** (rides, users, groups, chat HTTP, geo, ws) — ראו **`backend/README.md`**. |

**לסיכום בראיון:** *“ב-auth הפרדתי בין מה שחייב להיות סינכרוני בטרנזקציה לבין צדדיות שמוזזות ל-outbox/worker; bcrypt לא רץ על ה-event loop; ויש rate limit + pool מוגדר.”*

---

## 7ד. JWT — ביטול access מיידי (Redis denylist)

רעיון שמפתחים בכירים מכירים אבל ג׳וניורים לעתים לא מחברים: **JWT הוא stateless** — בלי מנגנון נוסף, אחרי “logout” ה-access עדיין **חתום ותקף** עד `exp`. כאן:

| רכיב | מה קורה |
|------|---------|
| **`jti`** | נוסף ל-access ב-`create_access_token` — מזהה הנפקה יחיד. |
| **Logout** | `AuthService.logout` מקבל את מחרוזת ה-access מ-**`Authorization`**, מפענח, לוקח `jti` + `exp`, **`TTL = max(0, int(exp_ts − now))`**, **`SETEX denylist:{jti}`**. |
| **בדיקה ב-HTTP** | אחרי `decode_access_token`, אם `jti` ב-denylist → **`InvalidAccessTokenError`** (או `None` ב-**`get_current_user_optional`**). |
| **Fail-open** | אם Redis נמוך ב-`is_denied` — **לא** חוסמים משתמש (זמינות); אם `add_to_denylist` נכשל — logout עדיין מצליח (refresh נמחק). |
| **WS handshake** | `get_current_user_ws` מיושר ל-HTTP ובודק denylist לפי `jti`; עדיין **אין** בדיקת `is_active` ב-WS handshake (בחירה להפחתת עומס DB תחת עומס חיבורים). |

**לראיון:** *“stateless JWT + denylist ב-Redis נותן logout אמיתי על access בלי טבלת טוקנים ב-Postgres.”*  
ADR: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §18**.

---

## 7ה. Idempotency-Key — בקשת הצטרפות מחיפוש (Stripe-style)

מניעת **כפילות booking** כשהלקוח לוחץ פעמיים או כשיש retry רשת — בלי לשנות את **`BookingService.request_to_join`** (לוגיקת דומיין נשארת שם):

| רכיב | מה קורה |
|------|---------|
| **כותרת** | **`Idempotency-Key`** אופציונלי על **`POST /passenger/passengers/request-ride-from-search`**. |
| **מפתח Redis** | `idempotency:request_ride:{user_id}:{client_key}` + `:fingerprint` ל-SHA-256 של גוף קנוני (`ride_id`, כתובות, מושבים). |
| **Claim** | **`SET … NX`** עם ערך `PROCESSING` — רק מנהיג אחד מבצע את יצירת `PassengerRequest` (אם צריך) + `request_to_join`. |
| **הצלחה** | שמירת JSON של **`BookingResponse`** (~5 דק׳ TTL); חזרה עם אותו מפתח ואותו fingerprint → **אותה תשובת 201**. |
| **בתהליך** | **409** + **`Retry-After: 1`**. |
| **Fingerprint שונה** | **422** (`idempotency_key_mismatch`). |
| **שגיאת דומיין** | מחיקת המפתח — לקוח יכול לנסות שוב (מפתח חדש). |
| **Fail-open** | Redis למטה → התנהגות כמו קודם (ללא dedup). |

**פרונט:** [`requestRideFromSearch`](../frontend/src/api/passengers.ts) מקבל מפתח אופציונלי; **[`useJoinRide`](../frontend/src/pages/SearchRides/useJoinRide.ts)** (נקרא מ־**[`useSearchRides`](../frontend/src/pages/SearchRides/useSearchRides.ts)**) יוצר **`crypto.randomUUID()`** פעם אחת לכל ניסיון הצטרפות (**`idempotencyKeyRef`**), מעביר ל-API, **מאפס אחרי הצלחה**, ומשאיר את המפתח אחרי שגיאה ל-retry עם אותו מפתח.

**גם בשליחת הודעה:** **`Idempotency-Key`** אופציונלי על **`POST /chat/conversations/{id}/messages`** — דפוס Stripe-style עם מפתח `idempotency:chat_message:{user_id}:{key}` ו-fingerprint על `conversation_id` + תוכן; פרונט: **[`sendMessage`](../frontend/src/api/chat.ts)** + **`useMessageThread`** / **`useChatPopup`** (מפתח ב-ref לניסיון, **`ChatListRow`** + **`applyInboundRealMessage`** / **`appendMessageDedupById`**, **`isChatIdempotencyKeyMismatch`**). ADR: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §25** (נסיעות: **§19**); פרונט: **`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` §2**; פיצ’ר UX: [FEATURE_DECISIONS.md#chat-optimistic-outbound](FEATURE_DECISIONS.md#chat-optimistic-outbound).

---

## 7ו. Chat XSS hardening — plaintext-only messages

כדי למנוע **stored XSS** בשכבת הצ'אט, הוגדרה מדיניות קלט של **טקסט בלבד**:

| רכיב | מה קורה |
|------|---------|
| **נקודת כניסה** | `MessageCreate` ב־`backend/app/domain/chat/schema.py` |
| **החלטת אבטחה** | `reject_html` דוחה הודעות שמכילות תגיות HTML (`<...>`) במקום לנקות אותן בשקט |
| **למה** | דחייה מפורשת שקופה יותר למשתמש ולמפתחים, ושומרת עקביות בין consumers שונים של תוכן הצ'אט (UI, WS, סיכומים/ייצוא עתידיים) |
| **מה זה לא** | לא מנגנון sanitization כללי ל-HTML — זו מדיניות מוצרית: צ'אט = plaintext |
| **בקצרה לראיון** | “בחרנו reject ל-HTML בהודעות צ'אט כדי לחסום payloads בעייתיים מוקדם ולשמור על UX צפוי: טקסט בלבד.” |

שכבה נוספת בדפדפן (הקשחת XSS/mixed content): **CSP מאוכף** על edge nginx עם `script-src` ללא **`'unsafe-inline'`** (**`/bootstrap.js`** הקדם‑טעינה של שפה ותמה), עם `report-uri` ל-Sentry — פירוט והבחנה מול SPA בלי SSR ב־**`docs/SECURITY_HEADERS.md`**.

---

## 8. AI וצ’אט “חכם”

- **טריגר ניתוח (בפועל בקוד):** לולאות **`task-worker`** (timeout שיחות) קוראות ישירות ל־`handle_conversation_completion` — **Groq** (מודל משפחת Llama דרך ה-API של Groq) → **`chat_analysis`** → Outbox (**`chat.conversation.completed`**).
- **בנוסף:** **ai-worker** מריץ **`run_chat_completion_redis_listener`** ל־`chat:completion:*` (מאזין). אין בשורות ה-Python הנבדקות ב־`backend/` פרסום לערוץ הזה; ראו [`docs/architecture/AI.md`](architecture/AI.md).
- ייצוא **iCal** ו-API לניתוח — ב-backend בלבד (לא ב-Go).

### FCM + מייל (איפה בקוד)

- **FCM (Backend)**: `app/domain/notifications/channels/push/client.py` — `messaging.Message` עם **`data` בלבד** (ללא `notification`), כולל `title` ו־`body` כמחרוזות + שדות metadata נוספים; שליחה ב-**`run_in_executor`** עם **`asyncio.get_running_loop()`**; **Tenacity** — retry רק על שגיאות transient של Firebase Admin (**`UnavailableError`**, **`InternalError`**, **`DeadlineExceededError`**, **`UnknownError`**), בלי retry על **`UnregisteredError`** / **`SenderIdMismatchError`**. `push_provider` שולח רק אם יש `fcm_token`; אם FCM מדווח רישום לא תקף — **ניקוי `users.fcm_token` ב-DB** דרך `crud_user.update_fcm_token` כש־**`db`** מועבר מה־handler (ראו `BaseNotificationProvider.send(..., db=None)` + `NotificationCommand.db`). מייל/WebSocket מתעלמים מ־`db`.
- **FCM (Frontend)**: `frontend/src/services/fcm.ts` — הרשאות, רישום SW, `getToken` + `PATCH /users/fcm-token`; **`cleanupFCM()`** מבטל `onMessage`. **AuthContext** — `initFCM()` אחרי login / Google / hydrate אם הרשאה `granted`; ב־logout: `patchFcmToken(null)` (בזמן JWT תקף) → `cleanupFCM()` → `logoutSession` → `clearTokens`. Toast גלובלי ב־**`App.tsx`** (`NotificationToast`). תפריט פרופיל: הפעלת התראות דרך **`useLayoutShell`**. בחזית `onMessage` → `title`/`body` מ־**`payload.data`** → Toast + צליל; ברקע `firebase-messaging-sw.js` — **`messaging.onBackgroundMessage`** עם **`payload.data`** (ללא מאזין `push` כפול). פירוט: **`docs/FCM_SYSTEM_SUMMARY.md`**.
- **מייל**: **Brevo** דרך `EmailClient` / `email_provider` — **circuit breaker** (`brevo_email_cb`) לפני קריאת ה-SDK; רינדור HTML דרך שירות ייעודי **`email-renderer`** (Node.js + Express + React Email). ה-backend שולח `template + props` ל-`POST /render` (`EMAIL_RENDERER_URL`), מפת התבניות מנוהלת ב-PascalCase ב-`email_conf.py`, ו-registry בצד renderer כולל fail-fast validation כדי ליפול ב-startup אם תבנית חסרה.

---

## 9. DevOps ופריסה

- **Docker Compose**: healthchecks (כולל **backend** על `/api/v1/health`), סיסמת Redis, volumes ל-RabbitMQ ו-Postgres; שירות **`migrate`** (`alembic upgrade head`, `restart: no`) לפני **backend** וכל ה-workers; שירותי פיתוח (`db`, `redis`, `rabbitmq`, `migrate`, `backend`, `notification-worker`, `task-worker`, `ai-worker`, `chat-ws`) ב־`docker compose up -d`; **frontend** סטטי + **nginx** באותו `docker-compose.yml` עם `profiles: ["prod"]` — סטאק מלא על פורט 80 עם `docker compose --profile prod up -d --build`, **nginx** אחרי **backend** ב־`service_healthy`. בפרודקשן Firebase עובד ב-Model B: `FIREBASE_CREDENTIALS_JSON` דרך `backend/.env` (ללא credentials file mount), ו-`FIREBASE_SERVICE_ACCOUNT_PATH` נשאר fallback לפיתוח מקומי בלבד. **פריסה בלי Compose** (למשל image בלבד / K8s): להריץ מיגרציה כ־Job או שלב init נפרד — לא מוטמע ב־`CMD` של image ה-production.
- **`.env` כפול לפי תפקיד:** `.env` **בשורש** (מ־`.env.example`) — רק credentials ש־Compose צורך להקמת Postgres / Redis / RabbitMQ; **`backend/.env`** — כל הגדרות הבקאנד. חייב **יישור** (סיסמאות DB/Redis/RabbitMQ) בין הקבצים. אחרי **שינוי `backend/.env`** — לרענן משתנים בקונטיינר: `docker compose up -d --force-recreate backend` (**לא** מספיק `restart` בלבד — ה-env נצרך בעת יצירת הקונטיינר).
- **גרסאות תמונות קבועות** (לא `latest` בשירותים קריטיים) — builds חוזרים.
- **K8s**: deployment ל-`chat-ws` עם env (למשל `BACKEND_URL`) ל-worker של last-seen.

---

## 10. איך להשתמש במסמך הזה בפורטפוליו

- בקורות חיים / לינקדאין: “Real-time chat (מקליד / מחובר / disconnect עם debounce), Go + Redis, Outbox+RabbitMQ, סינכרון מול אסינכרון, PostGIS”.
- בראיון: **סעיף 4** + **5** (real-time נסיעות + Zod) + **6** + **0א** (סיכום בעיה/החלטה/trade-off) + **7ג** (auth בעומס) + **7ד** (JWT denylist) + **7ה** (Idempotency — נסיעות + צ’אט, ADR **§19**/**§25**; billing checkout **§26** / [FEATURE_DECISIONS](FEATURE_DECISIONS.md#billing-checkout-db-idempotency-reconciler)) + **7ב** (defensive) + **Latest architecture updates** (Circuit Breaker Google Maps, **צ’אט `onOpen` + `after`**) + **12** + **13** + **14** (פרונט).

---

## 11. צ’ק-ליסט — מה מכוסה במסמך

| נושא | מכוסה |
|------|--------|
| התראת נוסע על נסיעה חדשה (Outbox `ride.created` → handler → מייל) | **סעיף 6.4** + `architecture/EVENTS.md` |
| מקליד / מחובר / disconnect | סעיף 4 |
| סינכרון / אסינכרון + RabbitMQ | סעיפים 6, **6.4** |
| Workers רצים תמיד vs מתוזמנים | סעיף 2א |
| AI (**Groq**; מודל משפחת Llama דרך ה-API) | סעיפים 2, 8 + [`architecture/AI.md`](architecture/AI.md) |
| FCM | סעיפים 1, 2, 8 + **`docs/FCM_SYSTEM_SUMMARY.md`** |
| מייל Brevo | סעיפים 1, 2, 6, 8 |
| כניסה עם Google | סעיפים 1, 2, 7א |
| אבטחה + rate limit + OTP + מאגר DB + enumeration + auth בעומס + JWT denylist + Idempotency (booking + צ’אט + billing checkout) | סעיפים 3, 7, 7א, **0א**, **7ג**, **7ד**, **7ה**, 7ב, 12 (+ **ADR §25**, **§26**) |
| ריפקטור פרונט (API, context, lazy, בדיקות) | **סעיף 14** + `frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md` |
| Zod, WebSocket (נסיעות/מיקום/צ’אט), reconnect (**REST gap** `fetchMissedGap` + **WS delay** [`reconnectBackoff.ts`](../frontend/src/utils/reconnectBackoff.ts)), `publish_ride_event` / `keys.py` | **סעיפים 1, 5, 14** + `frontend/src/types/wsEvents.ts` + [`FEATURE_DECISIONS.md#chat-thread-reconnect`](FEATURE_DECISIONS.md#chat-thread-reconnect) + [`FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff`](FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff) + [`fetchMissedGap.ts`](../frontend/src/pages/MessageThread/fetchMissedGap.ts) |
| Google Maps + circuit breaker / Brevo email CB (Directions + Distance Matrix + health) | **סעיף 2** (טבלת APIs), **Latest architecture updates**, סעיף **12** (גיאו), **`docs/architecture/NOTIFICATIONS.md`** |
| CI/CD, GHCR, S3 + CloudFront, מובייל, pytest, Vitest מקומי, k6, phonenumbers | **סעיפים 2, 9, 12** |
| Unread WS, קבוצות, SQLAdmin, UUID, RTL, EIA | **סעיף 13** |
| Defensive programming | **סעיף 7ב** |

---

## 12. דגשים נוספים (סקירה מעמיקה — מה להשוויץ)

נבדק מול הקוד וה-repo; אלה נקודות חזקות שלא תמיד בולטות ב”סיפור הראשי”:

### CI/CD ואיכות קוד

| מה | פירוט |
|----|--------|
| **GitHub Actions — workflows עם path filters** | **`backend-ci`**: Ruff (+ format check), Postgres שירות, **`DATABASE_URL=test_db`**, **`uv sync`**, **`uv run alembic upgrade head`**, **`scripts/ops/check-migration-head.sh`**, **`tests/infrastructure/test_rabbitmq_reliability.py`**, **`uv run pytest tests/`** + build/push ל-GHCR על `main`. **`frontend-ci`**, **`chat-ws-ci`**, **`email-renderer-ci`** — טריגר לפי `paths`. פריסת **production** ל-**EC2** ב־**[`deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml)** (`workflow_run` אחרי CI מוצלח), לא מ־GKE (מניפסטי **`k8s/`** בלי **`deploy-gke.yml`** — **`docs/FUTURE_WORK.md`**). |
| **Deploy אוטומטי ל-EC2** | אחרי הצלחת אחד מ־**Backend / Frontend / Chat-WS / Email renderer** CI על `main`: **`deploy-ec2.yml`** — SSH, compose מלא, smokes פנימיים + gate ל-backend, rollback עם fallback ל-**`backend:latest`**. פתרון פרגמטי ל-`t3.medium` בלי ALB. |
| **דחיפת images ל-GHCR** | על push ל-`main` מתוך **backend-ci** / **frontend-ci** / **chat-ws-ci** / **email-renderer-ci**: תמונות כמו **`ghcr.io/<owner>/linkup/backend`**, **`…/worker`**, **`…/migrate`**, **`…/pgbouncer`**, **`…/frontend`**, **`…/chat-ws`** ובנפרד **`ghcr.io/<owner>/linkup-email-renderer`** (ללא קידומת `linkup/`). |
| **uv ב-CI** | התקנת תלויות backend דרך `uv sync --frozen`; **`backend/uv.lock`** + **`backend/pyproject.toml`** — כולל נעילת **`phonenumbers==8.13.48`** לאימות מספרים ישראליים עקבי. |
| **Settings ↔ env (DB/Redis)** | `DATABASE_URL` / `REDIS_URL` מהסביבה נכנסים ל־`DATABASE_URL_RAW` / `REDIS_URL_RAW` דרך **`validation_alias=AliasChoices`** (pydantic-settings) + **`populate_by_name=True`** — Alembic ו-runtime רואים את אותו override כמו ב-CI (לא `json_schema_extra`). |
| **Redis broadcast — רשימת נסיעות** | שם ערוץ **`rides:list`** ב־`app/infrastructure/redis/keys.py` (`RIDES_LIST_CHANNEL`); ייבוא אחיד משירות הנסיעות. |
| **בדיקות אבטחה JWT** | `backend/tests/test_security.py` — טוקן תקין, פג תוקף, חתימה שגויה (מקרים קריטיים ל-auth). |
| **בדיקות auth + OWASP enumeration** | `backend/tests/test_auth.py` (דורש `DATABASE_URL`) — רישום, אימייל כפול, סיסמה שגויה ואימייל לא קיים → אותה שגיאת לוגין. |
| **בדיקות יחידה בפרונט (מקומי)** | Vitest — לדוגמה `frontend/src/utils/apiError.test.ts`, **`frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts`** (אירועי WS / Zod) (`npm run test`); לא חובה ב-CI כרגע (ה-workflow מריץ lint + build). |

### העלאות קבצים — לא דרך ה-API

| מה | פירוט |
|----|--------|
| **Presigned URLs (S3)** | הלקוח מעלה **ישירות ל-S3** (אווטאר + תמונת קבוצה) — ה-API לא עובר בו זרימת bytes; פחות עומס ו-timeoutים. |
| **CloudFront (קריאה)** | כש־**`CLOUDFRONT_DOMAIN`** מוגדר ב-backend, בניית URL לתמונות (אווטאר/קבוצות) משתמשת ב-**HTTPS לדומיין CloudFront** מול מפתח האובייקט — URL יציב ללקוחות ול-cache ב-CDN; בלי דומיין — **presigned GET** ל-S3. |
| **Pipeline אווטאר (גרסאות immutable)** | staging ב-S3 → תור **avatar_upload_queue** → worker (resize/WebP) → העלאה ל־**prefix חדש** `avatars/{user_id}/v{version}/` **בלי** מחיקת תיקיית משתמש לפני ההעלאה; עדכון `avatar_key` ב-DB; **מחיקת prefix הגרסה הקודמת** רק אחרי commit מוצלח; אם ה-commit נכשל — ניקוי best-effort של ה-prefix החדש (orphan). מחיקת אווטאר מה-API — מחיקת כל `avatars/{user_id}/` ב-S3. |
| **תיעוד CORS ל-bucket** | `docs/S3_CORS.md` — תצורה מודעת לדפדפן. |

### גיאו — שילוב מקורות

| מה | פירוט |
|----|--------|
| **Geocoding** | **Google Geocoding API** (`GeocodingService`) — כתובת→קואורדינטות ו-reverse; עטוף ב-Redis geocode cache (24h, fail-open) + **`google_geocoding_cb`**. |
| **מסלולים** | **Google Directions** + **Distance Matrix** (`GeoClient`) — **`google_directions_cb`** / **`google_distance_matrix_cb`**; **Maps JS** בפרונט. |
| **PostGIS** | שאילתות מרחביות וחיפוש נסיעות לפי מיקום. |
| **Geocode cache + stampede** | TTL **24 שעות**, מפתח `geocode:{address}`; **fail-open** אם Redis נופל; על **cold miss או פרץ מקבילי** על אותו מפתח — **`get_or_compute`** (נעילה + המתנה לערך מחושב יחיד) במקום N קריאות Google במקביל. קוד: [`geocode_cache.py`](../backend/app/infrastructure/geo/geocode_cache.py), [`cache_stampede.py`](../backend/app/infrastructure/redis/cache_stampede.py). תיעוד החלטה: [**FEATURE_DECISIONS** — geocode-cache-stampede](FEATURE_DECISIONS.md#geocode-cache-stampede). |
| **Circuit breaker (Maps + Brevo)** | מחלקה משותפת **`app/infrastructure/circuit_breaker.py`**; singletons גיאו ב־**`geo/circuit_breaker.py`**; **`brevo_email_cb`** ב־**`notifications/circuit_breaker.py`**. מצב **`closed` / `open` / `half_open`** ב־**`GET /api/v1/health`** תחת **`circuit_breakers`** (כולל **`brevo_email`**) — לא משנה את **`status`** הכללי של Health. |

### אבטחה HTTP מעבר ל-JWT

| מה | פירוט |
|----|--------|
| **Revocation ל-access** | **`jti`** ב-access + **`denylist:{jti}`** ב-Redis עד `exp` אחרי logout — לא רק ניקוי refresh ב-DB. |
| **Idempotent POST (נוסע)** | **`Idempotency-Key`** + **`SET NX`** + מטמון **201** ל־`request-ride-from-search` — דפוס Stripe; פירוט **§7ה**. |
| **Security headers + CSP (enforcing)** | Edge nginx: **`listen 443 ssl`** (HTTP/1.1 over TLS במאגר הנוכחי — אין `http2` ב־`listen` עד שמפעילים במפורש), HSTS (`includeSubDomains`, בלי `preload`), `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `COOP/COEP` ל־OAuth popup (**`FEATURE_DECISIONS`** `#oauth-popup-coop`). **CSP:** כותרת **`Content-Security-Policy`** מאוכפת; **`script-src`** ללא **`'unsafe-inline'`** (bootstrap ב־**`frontend/public/bootstrap.js`** לפני **`/config.js`**); **`style-src`** עם **`'unsafe-inline'`**; **`report-uri`** ל־Sentry CSP; **`frame-src`** ל־Stripe + Google Sign-In. פירוט: **`docs/SECURITY_HEADERS.md`**. |
| **CORS כפול** | middleware רגיל + **EnsureCORS** גם על תגובות שגיאה (כולל 500) — פחות “CORS נשבר רק על שגיאה”. |

### תשתית וסקייל — מה שכדאי להזכיר בראיון (מעבר לרשימה הראשית)

| מה | למה זה חשוב |
|----|----------------|
| **Redis — שני logical DB (0 ו-1)** | הפרדת cache/rate-limit/denylist/idempotency/pubsub-API מ-pub/sub של צ’אט והשלמות AI — פחות הפרעות והתנגשויות מפתחות. |
| **Geocode — mutex נגד stampede** | מסלול `get_coordinates` מאחד עומס מקבילי על כתובת קר למקור חיצוני אחד; מדדי `geo_cache_*` / `cache_stampede*` — **`docs/operations/MONITORING.md`**. |
| **Outbox LISTEN/NOTIFY** | עדיפות לאירוע אחרי commit לעומת polling גס בלבד — פחות latency ועומס על DB. |
| **Scheduled publisher replica=1** | מניעת כפל פרסום משימות מתוזמנות — דפוס קלאסי ב-job schedulers. |
| **Presigned PUT ל-S3** | ה-API לא מעביר bytes של תמונות — פחות CPU/זיכרון ו-timeoutים בשרת. |
| **Cursor pagination** | חיפוש נסיעות וצ’אט בלי offset עמוק — יציב יותר בנתונים גדלים. |
| **קונטרקט שגיאות אחיד** | `LinkUpError` + `trace_id` — לקוחות ו-Sentry מיושרים; פחות דיבוג “בעלם”. |
| **Sentry + Prometheus/Grafana (פעיל)** | **Sentry:** `sentry_sdk.init()` ב-`setup_logging()` כש-`SENTRY_DSN` מוגדר — FastAPI/SQLAlchemy/Redis integrations, `traces_sample_rate=0.1`; `capture_exception` ל-5xx בלבד (מניעת רעש). פרונט: `Sentry.init()` ב-`main.tsx` + `captureException` ב-axios interceptor (5xx), `ChatErrorBoundary`, `RouteErrorBoundary`, **BrowserTracing + Replay + Web Vitals (CLS/LCP/INP) עם dynamic import ו-sampling quota-safe**, ו-`Sentry.setUser` ב-auth lifecycle. **Prometheus/Grafana:** backend חושף `/metrics`; compose profile `monitoring` מרים `prometheus`+`grafana` עם provisioning + dashboard בסיסי. DSN ב-`.env` בלבד, לא ב-git. **קונסולות אופס (קישורים):** [`docs/operations/MONITORING.md`](operations/MONITORING.md) — Sentry Issues + Better Stack (uptime מול `/livez`). **שאילתות:** אין pipeline אוטומטי ל-EXPLAIN ANALYZE; סקירה ידנית מומלצת על נתיבים כבדים עם `pg_stat_statements`. |

### אימות טלפון (ישראל / בינלאומי)

| מה | פירוט |
|----|--------|
| **phonenumbers** | הולידציה ב־`app/core/utils/validators.py` עם ספריית **`phonenumbers`**. הגרסה **נעולה ל־`8.13.48`** ב־**`backend/pyproject.toml`** / **`backend/uv.lock`** — יציבות מול מטא־דאטה ישראלית (גרסאות 9.x שינו התנהגות לטווחי מנוי מסוימים). |

### מוצר ופלטפורמות

| מה | פירוט |
|----|--------|
| **Web + Mobile** | **React (Vite)** וגם אפליקציה ב-**Expo/React Native** (`mobile/`) — אותו REST API, לקוחות מרובים. |
| **אימות מייל** | קוד ב-**Redis** (TTL) + מייל דרך Brevo; resend verification; OTP מוגן (**`secrets`**, **`compare_digest`**, מונה ניסיונות). |
| **עומס auth + שכבות נוספות (Grafana k6)** | סקריפטים מאורגנים תחת **`backend/k6/scripts/`**: auth, rides core flows, users/profile, groups, chat HTTP, geo/maps, websocket. wrappers נשמרו ב-`backend/load_test.js` ו-`backend/load_test_rides.js` לתאימות. לפני ריצה: `DEBUG=True`, העלאת `RATE_LIMIT_AUTH_MAX_REQUESTS`, ו־`docker compose up -d --force-recreate backend`. |

### מסד וסכימה

| מה | פירוט |
|----|--------|
| **Alembic** | מיגרציות מסודרות; migration ייעודי **indexes** (rides, bookings, group_members, וכו’) + participants לצ’אט. |

### ניהול שגיאות API

| מה | פירוט |
|----|--------|
| **LinkUpError + handlers** | מרכוז טיפול בשגיאות + `X-Request-ID` בתגובה — עקביות לקוח ולוגים. |

---

## 13. עוד דגשים להצגה (סבב נוסף)

דברים מיוחדים שלא תופסים תמיד מקום ב”סיפור הראשי”:

| דגש | פירוט קצר |
|-----|-----------|
| **Unread צ’אט (בזמן אמת)** | אחרי **`send_message`** — פרסום ל־**`user:{recipient_id}:events`** עם **`invalidate`** + **`resource: unread_messages`** + **`count`**; **`useUserEventStream`** + **`setUnreadDirect`** ב־`ChatContext` מעדכנים את מטמון React Query בלי חובה ל־HTTP עד רפרש הבא (polling נשאר גיבוי ~30 שניות). |
| **Presence בצ’אט** | טעינה חד־פעמית ל-`GET /presence/{id}`; **`user_online` / `user_offline`** ב-WS לעדכון מיידי. |
| **קבוצות + הזמנה** | `invite_code` ייחודי, תפוגה אופציונלית, endpoint הצטרפות; העברת admin בקבוצה. |
| **SQLAdmin** | ממשק **ניהול DB** (FastAPI-SQLAdmin): משתמשים, נסיעות, הזמנות, בקשות — תפעול ודיבוג (נפרד ממסך האדמין ב־React). |
| **מסך אדמין מותאם (React)** | דשבורד אופרטיבי בפרונט הראשי — לא אפליקציית Vite נפרדת; אותו JWT, שער `AdminRoute`, והידרציה של `is_admin` אחרי לוגין. |
| **UUID כמפתחות** | `user_id`, `booking_id`, `ride_id` וכו’ — מניעת התנגשויות ומוכנות לפיצ’ול אופקי. |
| **RTL / עברית + EN** | פרונט ווב **RTL-first** עם מעבר שפה (עברית/אנגלית); Google Directions עם `language=he`. פורמט תאריכים/שעות לפי שפת הממשק. |
| **אגרגציה ב-WS (Go)** | Write pump מאחד כמה הודעות ל-**frame אחד** מופרד ב-`\n` — פחות overhead; הפרונט מפרק שורות ב-`onmessage`. |
| **Graceful shutdown ב-worker** | SIGINT/SIGTERM → ביטול tasks, סגירת RabbitMQ — לא “kill קשה” בלבד. |
| **EIA / דלק (מתוזמן)** | תשתית לסריקת מחירי דלק (מפתח `EIA_API_KEY`) — slot בתור המתוזמן. |

---

## 14. פרונט — ריפקטור וארגון (Vite / React)

מקור אמת מפורט לטבלאות סטטוס: **`frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md`**. סקירת מבנה קבצים: **`frontend/docs/ARCHITECTURE.md`**.

| ציר | פירוט |
|-----|--------|
| **שכבת API** | כל קריאת HTTP דרך `src/api/<תחום>.ts` — לא ייבוא ישיר של `api` מ־`client` בקומפוננטות (חריגים מתועדים: `AuthContext`, `presence.ts`). **`passengers.ts` / `useJoinRide`** — **`Idempotency-Key`** יציב לפעולה דרך **ref** (**§7ה**); **`chat.ts` / `sendMessage`** + **`useMessageThread`** / **`useChatPopup`** — מפתח יציב לניסיון שליחה, **`types/chatList`** (`ChatListRow`), **`applyInboundRealMessage`** / **`appendMessageDedupById`** (**`chatMessagesMerge`**), **`isChatIdempotencyKeyMismatch`** (**ADR §25**, **ADR Frontend §2**). |
| **שגיאות** | `getApiErrorMessage` / `getApiStatus` / `isTimeoutOrAbortError` ב־`utils/apiError.ts` + **Vitest** (`apiError.test.ts`). ב־hooks: fallback אחיד עם **`apiErr('err_*')`** (מפתחות ב־`common.json`) במקום מחרוזות עברית קשיחות. |
| **i18n / טיפוגרפיה** | **`LangContext`** — `lang`, `dir`, **`--font-primary`**; קבצי תרגום תחת `src/i18n/locales/`; ב־**`*.module.css`** — `var(--font-primary)` / `var(--font-numeric)` (חריג: `LangToggle`). |
| **Code splitting** | **`React.lazy` + `Suspense`** לדפים (טעינה עצלה), מסכי טעינה עקביים; **מסלולי `/admin/*`** נטענים עצלנית דרך מודול `features/admin`. |
| **State גלובלי** | **`ChatContext`** + `chatReducer`; **`GroupContext`** — רשימת קבוצות, `activeChipId` משותף ל־**MyRides** / **MyRequests** (פילטר צ’יפים); איפוס צ’יפ אחרי leave/close קבוצה בזרימות ניהול. |
| **פיד התראות (in-app)** | **`useChatNotificationsFeed`** — REST + polling **~5 דקות**; רענון חי מ־**`invalidate`** / **`UserEvent`** ב־**`useUserEventStream`** (מאזין יחיד ב־**`ChatContext`**, לא ב־Layout): **`NOTIFICATIONS_REFRESH_EVENT`** + **`linkup:user-event`** (בתנאי) בענף **`notifications`**. |
| **בקשות נוסע** | הוק **`useMyRequests`** — לוגיקת MyRequests מרוכזת. |
| **הזמנות שלי (VM)** | **`useMyBookings`** — קומפוזיציה מ־`useMyBookingsPassenger` + `useMyBookingsDriver`; החזרה **מקוננת** (`passenger`, `driver`, `chat`) + יצוא **`MyBookingsViewModel`**. טעינה ב־**קריאת REST אחת לטאב** (`/bookings/driver-summary`, `/bookings/passenger-summary`) במקום N+1. כרטיס נוסע: **`PassengerBookingCard`**. |
| **עיצוב** | **`tokens.css`**, `ThemeContext`, מצב כהה — פחות אינליין CSS בדפי auth. |
| **איכות** | בדיקות יחידה ל־reducer ול־utils קריטיים (`chatReducer`, `apiError`, **`chatMessagesMerge`**, `myBookings.utils`, MessageThread WS, `ErrorBanner`) לפי [`FRONTEND_REFACTOR_AND_QUALITY.md`](../frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md). |
| **Zod + WebSocket** | סכימות ב־**`src/types/wsEvents.ts`**; אימות בכניסה ב־hooks וב־**`processChatWebSocketMessage`** — ראו **סעיף 5**. |

*בראיון:* “פרדתי שכבת API, פיצלתי דפים כבדים להוקים, ואיחדתי פילטר קבוצות ב-context כדי שלא יישבר בין מסכים.”

---

*עודכן כחלק מתיעוד הפרויקט — כולל מאגר DB ניתן להגדרה, **auth בעומס** (bcrypt ב-executor, pool, rate limit, outbox), **`jti` + Redis denylist ל-access אחרי logout** (ADR §18), **Idempotency-Key** לבקשת הצטרפות מחיפוש (ADR §19, **`passengers.ts`**, **`useJoinRide.ts`** + **`useSearchRides.ts`**) ולשליחת הודעת צ’אט (ADR §25 + Frontend ADR §2, **`message_idempotency.py`**, **`chat.ts`**, **`sendMessage`**, **`useMessageThread`**, **`useChatPopup`**, **`chatMessagesMerge`**, **`ChatListRow` / optimistic UI**), **השלמת הודעות צ’אט אחרי reconnect** (**`useChatWebSocket`** / **`useConversationMessages`**, **`FEATURE_DECISIONS`** chat-thread-reconnect), **פרונט: WS reconnect backoff + jitter** ([**`reconnectBackoff.ts`**](../frontend/src/utils/reconnectBackoff.ts), **`FEATURE_DECISIONS`** frontend-ws-reconnect-backoff), **Circuit Breaker** — מחלקה משותפת **`infrastructure/circuit_breaker.py`**, גיאו ב־**`geo/circuit_breaker.py`**, Brevo ב־**`notifications/circuit_breaker.py`** + **`circuit_breakers` ב-`/api/v1/health`** (ADR §20), **PgBouncer ממומש ב-Compose** (internal-only + migration isolation + asyncpg compatibility), **structlog + `X-Request-ID` / ContextVar** (`ARCHITECTURE.md` — Observability), סעיף **0א** (סיכום trade-offs), חיזוק OTP, מניעת user enumeration בלוגין (OWASP), **GitHub Actions + GHCR** (backend: **Ruff** → **Alembic upgrade head** → **pytest** עם **`DATABASE_URL` אחיד**; chat-ws: **go build** + **go vet**), **pydantic-settings** (`validation_alias` ל־`DATABASE_URL` / `REDIS_URL`), **Vitest + ריפקטור ארגון בפרונט** (`FRONTEND_REFACTOR_AND_QUALITY.md`), **Zod לאימות WebSocket** (`frontend/src/types/wsEvents.ts`), **מסך אדמין דסקטופ** (`ADMIN_DASHBOARD.md`, `/admin` + `/api/v1/admin`), **k6** עם דוגמת תוצאות, **phonenumbers==8.13.48**, **S3 + CloudFront (קריאה ציבורית) ואווטאר ב-prefix גרסתי immutable**, **i18n + לוקאליזציה + `apiErr` + פונטים ב־CSS Modules** (`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` §10–12), ו-**Docker Compose** (שירות **migrate**, healthcheck ל-backend, `.env` בשורש + `backend/.env`, recreate לקונטיינר אחרי שינוי env).*
