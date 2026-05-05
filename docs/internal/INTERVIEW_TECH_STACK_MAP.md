# LinkUp — מיפוי טכנולוגיות לראיון (מול קורות החיים)

מסמך זה **משלים** את [`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md): לכל ניסוח טיפוסי בקורות החיים / בפיץ’ — **איפה זה מופיע בפועל בפרויקט** (שירותים, תיקיות, קבצים מרכזיים). מומלץ להדפיס או לפתוח לצד ההיילייטס בראיון.

**שורת CV (אנגלית) — עוגן:**  
*LinkUp — Full-Stack Ride-Sharing Platform | React, TypeScript, Python, Go, Node.js, PostgreSQL, Redis (2025–2026)*

---

## 1. Full-stack + Ride-sharing (המוצר)

| בקורות חיים | בפרויקט |
|-------------|---------|
| פלטפורמת נסיעות משותפות end-to-end | דומיינים: נסיעות, נוסעים, הזמנות, קבוצות, צ’אט, התראות, משתמשים — ראו סיכום טבלאות ב-[`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) §1; API ב-[`docs/architecture/API.md`](../architecture/API.md). |

---

## 2. React + TypeScript frontend

| בקורות חיים | בפרויקט |
|-------------|---------|
| SPA מודרנית | [`frontend/`](../../frontend/) — Vite, `src/` (דפים, hooks, features). |
| TypeScript | קבצי `.ts` / `.tsx`; לדוגמה טיפוסי API ב-`frontend/src/types/`, סכימות WS ב-`frontend/src/types/wsEvents.ts` (עם Zod). |
| i18n (תוספת מוצרית) | `frontend/src/i18n/` (he/en), שימוש ב-hooks כמו `useTranslation`. |
| Auth — ניתוק סשן מאוחד (web) | **`tearDownSession`** ב-[`AuthContext.tsx`](../../frontend/src/context/AuthContext.tsx), **`emitSessionExpired` / refresh** ב-[`client.ts`](../../frontend/src/api/client.ts), סינון Sentry ל-401 ב-[`queryClient.ts`](../../frontend/src/api/queryClient.ts) — [`FEATURE_DECISIONS.md`](../FEATURE_DECISIONS.md#auth-session-teardown), **ADR §21**. |

---

## 3. REST APIs

| בקורות חיים | בפרויקט |
|-------------|---------|
| API מובנה | **FastAPI** תחת [`backend/app/`](../../backend/app/) — ראוטרים לפי דומיין (למשל `domain/rides`, `domain/bookings`, `domain/passengers`). |
| גרסת API | קידומת נפוצה: `/api/v1/...` (בריאות, נסיעות, צ’אט HTTP, גיאו, אדמין). |
| תיעוד ארכיטקטורה | [`docs/architecture/API.md`](../architecture/API.md), [`ARCHITECTURE.md`](../ARCHITECTURE.md). |

---

## 4. Real-time WebSocket — Go + Redis Pub/Sub

| בקורות חיים | בפרויקט |
|-------------|---------|
| שרת WS ייעודי ב-Go | [`chat-ws/`](../../chat-ws/) — `go.mod`, Dockerfile, subscribe/publish; ה־hub: **`SetReadLimit(2048)`**, **`x/time/rate`** על פרסום **typing בלבד** (§7 ב-ADR). |
| Redis Pub/Sub לצ’אט | ה-API שומר הודעה ומפרסם לערוץ; `chat-ws` נרשם — פירוט זרימה ב-[`docs/architecture/REALTIME.md`](../architecture/REALTIME.md), ADR ב-[`docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md`](../adr/ARCHITECTURE_DECISIONS_CHAT_WS.md) (§7 inbound). |
| פרונט — pacing ל־reconnect | [`reconnectBackoff.ts`](../../frontend/src/utils/reconnectBackoff.ts) (`computeReconnectDelayMs`) — **`useChatWebSocket`**, **`useUserEventStream`** (עוטף **`useReconnectingWebSocket`** ל-chat-ws), **`useRideWebSocket`** (נסיעות FastAPI), **`useReconnectingWebSocketState`** (GPS); [`FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff`](../FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff). |
| הפרדת DB Redis | DB **0** (cache, broadcast rides, rate limit וכו’) מול DB **1** (צ’אט + `user:{id}:events`) — [`docker-compose.yml`](../../docker-compose.yml), [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) §2. |

---

## 5. Node.js microservice — Express + TypeScript + React Email

| בקורות חיים | בפרויקט |
|-------------|---------|
| שירות רינדור HTML למיילים | [`email-renderer/`](../../email-renderer/) — `src/server.ts` (**Express**), `POST /render`, `GET /health`. |
| תבניות React Email | `email-renderer/src/emails/templates/`, `registry.ts`, רכיבים ב-`components/`. |
| אינטגרציה מהבקאנד | משתני סביבה כמו `EMAIL_RENDERER_URL`; worker/backend קוראים לרינדור לפני שליחה (Brevo) — ראו גם [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) §5. |
| פריסה | שירות `email-renderer` ב-[`docker-compose.yml`](../../docker-compose.yml); מניפסטים תחת [`k8s/email-renderer/`](../../k8s/email-renderer/); CI: [`.github/workflows/email-renderer-ci.yml`](../../.github/workflows/email-renderer-ci.yml). |

---

## 6. Microservices-style workers

| בקורות חיים | בפרויקט |
|-------------|---------|
| Worker נפרד מה-API | תהליכי **`notification-worker`**, **`task-worker`**, **`ai-worker`** (אותו codebase Python, entries נפרדים) — outbox dispatch, notifications, scheduled/avatar tasks, AI completion — [`docs/ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) §2א, [`docs/architecture/EVENTS.md`](../architecture/EVENTS.md). |
| תורים נפרדים | למשל `notifications_queue`, `avatar_upload_queue`, `scheduled_tasks_queue`. |

---

## 7. Outbox pattern + RabbitMQ

| בקורות חיים | בפרויקט |
|-------------|---------|
| Outbox | טבלת `outbox_events`, פרסום אחרי commit — [`backend/app/infrastructure/outbox/`](../../backend/app/infrastructure/outbox/), ADR §4 ב-[`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md). |
| RabbitMQ | שירות `rabbitmq` ב-Compose; routing keys / exchanges — `EVENTS.md`, ADR §3. |

---

## 8. PostgreSQL + PostGIS (geo queries)

| בקורות חיים | בפרויקט |
|-------------|---------|
| PostGIS | אימג’ `postgis/postgis` ל-DB ב-Compose; גיאומטריה וחיפוש מרחבי בדומיין נסיעות/נוסעים. |
| תיעוד סכמה | [`docs/architecture/DATABASE.md`](../architecture/DATABASE.md). |

---

## 9. Redis

| בקורות חיים | בפרויקט |
|-------------|---------|
| Cache, rate limit, pub/sub, denylist, idempotency | שימושים: geocode cache (**כולל mutex/stampede** — [`cache_stampede.py`](../../backend/app/infrastructure/redis/cache_stampede.py), [`FEATURE_DECISIONS.md`](../FEATURE_DECISIONS.md#geocode-cache-stampede)), ride preview, OTP, auth rate limit, **JWT denylist (`denylist:{jti}`)**, **Idempotency-Key** ל־**`request-ride-from-search`** ול־**POST הודעת צ’אט** (`SET NX`, fingerprint), broadcast, צ’אט — מסוכמים ב-ADR §18–**§19**, **§25**, Frontend ADR §2, ובהיילייטס §2–3, **§7ד**, **§7ה**. **פרונט:** **`useJoinRide`** (ref); **`useMessageThread`** / **`useChatPopup`** + **`ChatListRow`** + **`applyInboundRealMessage`** / **`appendMessageDedupById`**. |

---

## 10. AWS S3 + CloudFront (presigned, avatars, CDN)

| בקורות חיים | בפרויקט |
|-------------|---------|
| העלאות presigned | זרימת PUT חתומה מהקליינט ל-S3 (אווטארים / קבוצות) — תיאור בהיילייטס §2 (מדיה) וקוד אינפרה תחת דומיין משתמשים/קבוצות. |
| אווטארים גרסתיים | prefix `avatars/{user_id}/v{version}/`, מחיקת גרסה קודמת אחרי commit — [`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) §2. |
| CloudFront | משתנה `CLOUDFRONT_DOMAIN` ל-URLs יציבים לקריאה; בלעדיות S3 כשלא מוגדר — אותו מקטע בהיילייטס. |

---

## 11. FCM push notifications

| בקורות חיים | בפרויקט |
|-------------|---------|
| Firebase Admin / FCM | אינטגרציה מה-worker והתראות; **שליחה ב-`data` בלבד** (בלי `notification` של FCM); retry על transient בלבד; ניקוי **`fcm_token`** ב-DB כשהרישום לא תקף (**`UnregisteredError`** / **`SenderIdMismatchError`**) — [`docs/adr/FCM_AND_PUSH.md`](../adr/FCM_AND_PUSH.md), [`docs/FCM_SYSTEM_SUMMARY.md`](../FCM_SYSTEM_SUMMARY.md), [`docs/architecture/NOTIFICATIONS.md`](../architecture/NOTIFICATIONS.md). |
| פרונט | Service Worker + Toast בחזית; גרסת compat ב-SW מיושרת ל-**`firebase` npm** — מפורט ב-FCM_SYSTEM_SUMMARY ובהיילייטס §8. |

---

## 12. AI chat summaries (Groq)

| בקורות חיים | בפרויקט |
|-------------|---------|
| ניתוח שיחה אחרי סגירה | **`task-worker`** scheduled (idle timeout) → `handle_conversation_completion` → **Groq** → **`chat_analysis`** + Outbox; בנוסף **`ai-worker`** מאזין ל־`chat:completion:*` — ראו [`architecture/AI.md`](../architecture/AI.md), [`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) §8; ADR §15. |

---

## 13. Google OAuth + JWT + bcrypt + rate limiting (OWASP-style)

| בקורות חיים | בפרויקט |
|-------------|---------|
| Google Sign-In | אימות `id_token` בבקאנד — [`backend/docs/GOOGLE_OAUTH.md`](../../backend/docs/GOOGLE_OAUTH.md). |
| JWT + Refresh | טוקנים ורענון ב-DB; **access עם `jti`**; **logout** מוסיף denylist ב-Redis — [`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) **§7ד**, ADR §18. |
| bcrypt ללא חסימת event loop | `run_in_executor` — ADR §12 ב-backend ADR. |
| Rate limiting | Redis על register/login — ADR §12, מימוש ב-auth domain. |
| מניעת user enumeration | אותה תגובת שגיאה ללוגין — ADR §12. |

---

## 14. Pessimistic locking

| בקורות חיים | בפרויקט |
|-------------|---------|
| `SELECT … FOR UPDATE` | נסיעות: [`backend/app/domain/rides/crud.py`](../../backend/app/domain/rides/crud.py) (`get_for_update`); הזמנות: [`backend/app/domain/bookings/crud.py`](../../backend/app/domain/bookings/crud.py) (`get_ride_for_update`); שירותים קוראים לפני אישור/ביטול/עדכון מושבים. |
| Outbox row lock | `with_for_update(skip_locked=True)` ב-[`backend/app/infrastructure/outbox/repository.py`](../../backend/app/infrastructure/outbox/repository.py). |

---

## 15. Async SQLAlchemy 2.0

| בקורות חיים | בפרויקט |
|-------------|---------|
| async session / `await` על DB | דומיינים ליבה: passengers, bookings, rides — שימוש ב-`AsyncSession`, `select`, `await db.execute` — ראו גם ADR §7 ב-backend ADR. |
| מיגרציות | **Alembic** תחת [`backend/`](../../backend/) (גרסאות סכמה). |

---

## 16. Unified API error handling

| בקורות חיים | בפרויקט |
|-------------|---------|
| `LinkUpError` + `error_code` + `trace_id` | [`backend/app/core/exceptions/`](../../backend/app/core/exceptions/), handlers ב-`main.py` — [`docs/ERRORS.md`](../ERRORS.md), סיכום ב-[`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) §2ב. |
| Frontend | `useErrorHandler`, `i18nError` / מפתחות `common:err_*` — בהיילייטס §2. |
| chat-ws | תגובות וקודי סגירה מתועדים — `ERRORS.md`. |

---

## 17. k6 load testing

| בקורות חיים | בפרויקט |
|-------------|---------|
| סקריפטי עומס | [`backend/k6/scripts/`](../../backend/k6/scripts/) — `load_test_auth.js`, `load_test_rides.js`, `load_test_groups.js`, `load_test_geo.js`, `load_test_chat.js`, `load_test_ws.js`, `load_test_users.js`. |
| הוראות | [`backend/k6/README.md`](../../backend/k6/README.md). |

---

## 18. CI/CD + Docker + Kubernetes

| בקורות חיים | בפרויקט |
|-------------|---------|
| Docker Compose (מקומי / אינטגרציה) | [`docker-compose.yml`](../../docker-compose.yml) — db, redis, rabbitmq, migrate, **email-renderer**, backend, **notification-worker**, **task-worker**, **ai-worker**, **chat-ws**; פרופיל prod עם frontend + nginx. |
| Edge nginx — TLS, headers, **CSP מאוכף** (`script-src` ללא `'unsafe-inline'`; bootstrap ב־[`frontend/public/bootstrap.js`](../../frontend/public/bootstrap.js) נטען ב־[`frontend/index.html`](../../frontend/index.html) **לפני** `/config.js`), `report-uri` מ־**`SENTRY_REPORT_URI`** (`backend/.env`) | [`nginx/nginx.conf.template`](../../nginx/nginx.conf.template) + [`scripts/ops/render-nginx-conf.sh`](../../scripts/ops/render-nginx-conf.sh) → `nginx/nginx.conf` (לא ב־Git); **`listen 443 ssl`** (בטמפלייט: HTTP/1.1 מעל TLS אלא אם מוסיפים `http2`); מדריך [`docs/SECURITY_HEADERS.md`](../SECURITY_HEADERS.md), החלטה [`FEATURE_DECISIONS.md`](../FEATURE_DECISIONS.md#browser-csp-edge). |
| GitHub Actions | [`.github/workflows/`](../../.github/workflows/) — `backend-ci` / `frontend-ci` / `chat-ws-ci` / `email-renderer-ci` (בנייה + push ל-GHCR לפי `paths`); **`deploy-ec2.yml`** (`workflow_run`) — פריסת Compose ל-EC2 אחרי CI ירוק על `main`. מניפסטי GKE תחת [`k8s/`](../../k8s/) בלי **`deploy-gke.yml`** — [`docs/FUTURE_WORK.md`](../FUTURE_WORK.md). |
| Dependabot | [`.github/dependabot.yml`](../../.github/dependabot.yml) — npm **`/frontend`**, pip **`/backend`**, Docker **`/backend`**, **`/frontend`**, **`/infrastructure/pgbouncer`**. |
| Kubernetes | [`k8s/`](../../k8s/) — base, overlays, infra (Postgres, Redis, RabbitMQ), שירותים נפרדים ל-backend, worker, chat-ws, email-renderer, frontend. |

---

## 19. Google Maps Platform (backend) + Circuit Breaker (Maps + Brevo)

| בקורות חיים | בפרויקט |
|-------------|---------|
| הגנה על תלות חיצונית (Maps + Brevo) | מחלקה משותפת [`backend/app/infrastructure/circuit_breaker.py`](../../backend/app/infrastructure/circuit_breaker.py); **גיאו:** singletons ב־[`geo/circuit_breaker.py`](../../backend/app/infrastructure/geo/circuit_breaker.py) + שימוש ב־[`geocoding.py`](../../backend/app/infrastructure/geo/geocoding.py) / [`client.py`](../../backend/app/infrastructure/geo/client.py). **מייל:** [`notifications/circuit_breaker.py`](../../backend/app/infrastructure/notifications/circuit_breaker.py) + [`email/client.py`](../../backend/app/domain/notifications/channels/email/client.py). |
| ניטור | מצב מעגלים ב־**`GET /api/v1/health`** תחת **`circuit_breakers`** (כולל **`brevo_email`**) — מדדי `geo_circuit_breaker_state` / `brevo_circuit_breaker_state` — [`docs/architecture/API.md`](../architecture/API.md#health), [`docs/operations/MONITORING.md`](../operations/MONITORING.md), ADR [**§20**](../adr/ARCHITECTURE_DECISIONS_BACKEND.md), [`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md). |

---

## קישורים מהירים לראיון

| נושא | מסמך |
|------|------|
| סיפור “מה בנינו” + דגשים | [`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md) |
| ניטור פרודקשן (Sentry + Better Stack) | [`docs/operations/MONITORING.md`](../operations/MONITORING.md#external-dashboards-production) |
| החלטות backend/worker | [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](../adr/ARCHITECTURE_DECISIONS_BACKEND.md) (כולל **§20** — Circuit Breaker: Maps + Brevo) |
| WS מתי ולמה | [`docs/adr/WEBSOCKETS.md`](../adr/WEBSOCKETS.md) |
| FCM | [`docs/adr/FCM_AND_PUSH.md`](../adr/FCM_AND_PUSH.md) |
| סקירה כללית | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |

---

*נוצר כמסמך מקביל לקורות חיים — עדכן אם הוספת שירות או שינית שם תיקייה קריטי.*

