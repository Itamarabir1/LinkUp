# LinkUp — מיפוי טכנולוגיות לראיון (מול קורות החיים)

מסמך זה **משלים** את [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md): לכל ניסוח טיפוסי בקורות החיים / בפיץ’ — **איפה זה מופיע בפועל בפרויקט** (שירותים, תיקיות, קבצים מרכזיים). מומלץ להדפיס או לפתוח לצד ההיילייטס בראיון.

**שורת CV (אנגלית) — עוגן:**  
*LinkUp — Full-Stack Ride-Sharing Platform | React, TypeScript, Python, Go, Node.js, PostgreSQL, Redis (2025–2026)*

---

## 1. Full-stack + Ride-sharing (המוצר)

| בקורות חיים | בפרויקט |
|-------------|---------|
| פלטפורמת נסיעות משותפות end-to-end | דומיינים: נסיעות, נוסעים, הזמנות, קבוצות, צ’אט, התראות, משתמשים — ראו סיכום טבלאות ב-[`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) §1; API ב-[`docs/architecture/API.md`](architecture/API.md). |

---

## 2. React + TypeScript frontend

| בקורות חיים | בפרויקט |
|-------------|---------|
| SPA מודרנית | [`frontend/`](../../frontend/) — Vite, `src/` (דפים, hooks, features). |
| TypeScript | קבצי `.ts` / `.tsx`; לדוגמה טיפוסי API ב-`frontend/src/types/`, סכימות WS ב-`frontend/src/types/wsEvents.ts` (עם Zod). |
| i18n (תוספת מוצרית) | `frontend/src/i18n/` (he/en), שימוש ב-hooks כמו `useTranslation`. |

---

## 3. REST APIs

| בקורות חיים | בפרויקט |
|-------------|---------|
| API מובנה | **FastAPI** תחת [`backend/app/`](../../backend/app/) — ראוטרים לפי דומיין (למשל `domain/rides`, `domain/bookings`, `domain/passengers`). |
| גרסת API | קידומת נפוצה: `/api/v1/...` (בריאות, נסיעות, צ’אט HTTP, גיאו, אדמין). |
| תיעוד ארכיטקטורה | [`docs/architecture/API.md`](architecture/API.md), [`ARCHITECTURE.md`](../ARCHITECTURE.md). |

---

## 4. Real-time WebSocket — Go + Redis Pub/Sub

| בקורות חיים | בפרויקט |
|-------------|---------|
| שרת WS ייעודי ב-Go | [`chat-ws/`](../../chat-ws/) — `go.mod`, Dockerfile, לוגיקת subscribe/publish. |
| Redis Pub/Sub לצ’אט | ה-API שומר הודעה ומפרסם לערוץ; `chat-ws` נרשם — פירוט זרימה ב-[`docs/architecture/REALTIME.md`](architecture/REALTIME.md), ADR ב-[`docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md`](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md). |
| הפרדת DB Redis | DB **0** (cache, broadcast rides, rate limit וכו’) מול DB **1** (צ’אט + `user:{id}:events`) — [`docker-compose.yml`](../../docker-compose.yml), [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md) §2. |

---

## 5. Node.js microservice — Express + TypeScript + React Email

| בקורות חיים | בפרויקט |
|-------------|---------|
| שירות רינדור HTML למיילים | [`email-renderer/`](../../email-renderer/) — `src/server.ts` (**Express**), `POST /render`, `GET /health`. |
| תבניות React Email | `email-renderer/src/emails/templates/`, `registry.ts`, רכיבים ב-`components/`. |
| אינטגרציה מהבקאנד | משתני סביבה כמו `EMAIL_RENDERER_URL`; worker/backend קוראים לרינדור לפני שליחה (Brevo) — ראו גם [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md) §5. |
| פריסה | שירות `email-renderer` ב-[`docker-compose.yml`](../../docker-compose.yml); מניפסטים תחת [`k8s/email-renderer/`](../../k8s/email-renderer/); CI: [`.github/workflows/email-renderer-ci.yml`](../../.github/workflows/email-renderer-ci.yml). |

---

## 6. Microservices-style workers

| בקורות חיים | בפרויקט |
|-------------|---------|
| Worker נפרד מה-API | תהליכי **`notification-worker`**, **`task-worker`**, **`ai-worker`** (אותו codebase Python, entries נפרדים) — outbox dispatch, notifications, scheduled/avatar tasks, AI completion — [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) §2א, [`docs/architecture/EVENTS.md`](architecture/EVENTS.md). |
| תורים נפרדים | למשל `notifications_queue`, `avatar_upload_queue`, `scheduled_tasks_queue`. |

---

## 7. Outbox pattern + RabbitMQ

| בקורות חיים | בפרויקט |
|-------------|---------|
| Outbox | טבלת `outbox_events`, פרסום אחרי commit — [`backend/app/infrastructure/outbox/`](../../backend/app/infrastructure/outbox/), ADR §4 ב-[`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md). |
| RabbitMQ | שירות `rabbitmq` ב-Compose; routing keys / exchanges — `EVENTS.md`, ADR §3. |

---

## 8. PostgreSQL + PostGIS (geo queries)

| בקורות חיים | בפרויקט |
|-------------|---------|
| PostGIS | אימג’ `postgis/postgis` ל-DB ב-Compose; גיאומטריה וחיפוש מרחבי בדומיין נסיעות/נוסעים. |
| תיעוד סכמה | [`docs/architecture/DATABASE.md`](architecture/DATABASE.md). |

---

## 9. Redis

| בקורות חיים | בפרויקט |
|-------------|---------|
| Cache, rate limit, pub/sub, denylist, idempotency | שימושים: geocode cache, ride preview, OTP, auth rate limit, **JWT denylist (`denylist:{jti}`)**, **Idempotency-Key** ל־**`request-ride-from-search`** (`SET NX`, fingerprint), broadcast, צ’אט — מסוכמים ב-ADR §18–**§19** ובהיילייטס §2–3, **§7ד**, **§7ה**. |

---

## 10. AWS S3 + CloudFront (presigned, avatars, CDN)

| בקורות חיים | בפרויקט |
|-------------|---------|
| העלאות presigned | זרימת PUT חתומה מהקליינט ל-S3 (אווטארים / קבוצות) — תיאור בהיילייטס §2 (מדיה) וקוד אינפרה תחת דומיין משתמשים/קבוצות. |
| אווטארים גרסתיים | prefix `avatars/{user_id}/v{version}/`, מחיקת גרסה קודמת אחרי commit — [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) §2. |
| CloudFront | משתנה `CLOUDFRONT_DOMAIN` ל-URLs יציבים לקריאה; בלעדיות S3 כשלא מוגדר — אותו מקטע בהיילייטס. |

---

## 11. FCM push notifications

| בקורות חיים | בפרויקט |
|-------------|---------|
| Firebase Admin / FCM | אינטגרציה מה-worker והתראות; **שליחה ב-`data` בלבד** (בלי `notification` של FCM) — [`docs/adr/FCM_AND_PUSH.md`](adr/FCM_AND_PUSH.md), [`docs/FCM_SYSTEM_SUMMARY.md`](FCM_SYSTEM_SUMMARY.md). |
| פרונט | Service Worker + Toast בחזית — מפורט ב-FCM_AND_PUSH ובהיילייטס §1–2. |

---

## 12. AI chat summaries (Groq)

| בקורות חיים | בפרויקט |
|-------------|---------|
| ניתוח שיחה אחרי סגירה | מאזין Redis (`chat:completion:*`) ב-worker → קריאה ל-**Groq** → שמירה — [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) §1–2א; ADR §15 ב-[`ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md). |

---

## 13. Google OAuth + JWT + bcrypt + rate limiting (OWASP-style)

| בקורות חיים | בפרויקט |
|-------------|---------|
| Google Sign-In | אימות `id_token` בבקאנד — [`backend/docs/GOOGLE_OAUTH.md`](../../backend/docs/GOOGLE_OAUTH.md). |
| JWT + Refresh | טוקנים ורענון ב-DB; **access עם `jti`**; **logout** מוסיף denylist ב-Redis — [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) **§7ד**, ADR §18. |
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
| `LinkUpError` + `error_code` + `trace_id` | [`backend/app/core/exceptions/`](../../backend/app/core/exceptions/), handlers ב-`main.py` — [`docs/ERRORS.md`](ERRORS.md), סיכום ב-[`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) §2ב. |
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
| GitHub Actions | [`.github/workflows/`](../../.github/workflows/) — `backend-ci`, `frontend-ci`, `chat-ws-ci`, `email-renderer-ci`; פריסה: `deploy-gke.yml`. |
| Kubernetes | [`k8s/`](../../k8s/) — base, overlays, infra (Postgres, Redis, RabbitMQ), שירותים נפרדים ל-backend, worker, chat-ws, email-renderer, frontend. |

---

## 19. Google Maps Platform (backend) + Circuit Breaker

| בקורות חיים | בפרויקט |
|-------------|---------|
| הגנה על תלות חיצונית (Maps APIs) | שלושה **singletons** ב־[`backend/app/infrastructure/geo/circuit_breaker.py`](../../backend/app/infrastructure/geo/circuit_breaker.py); אינטגרציה ב־[`geocoding.py`](../../backend/app/infrastructure/geo/geocoding.py) ו־[`client.py`](../../backend/app/infrastructure/geo/client.py). |
| ניטור | מצב מעגלים ב־**`GET /api/v1/health`** תחת **`circuit_breakers`** — [`docs/architecture/API.md`](architecture/API.md#health), ADR [**§20**](adr/ARCHITECTURE_DECISIONS_BACKEND.md), [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) (Latest architecture updates). |

---

## קישורים מהירים לראיון

| נושא | מסמך |
|------|------|
| סיפור “מה בנינו” + דגשים | [`ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) |
| החלטות backend/worker | [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md) (כולל **§20** — Circuit Breaker ל-Google Maps) |
| WS מתי ולמה | [`docs/adr/WEBSOCKETS.md`](adr/WEBSOCKETS.md) |
| FCM | [`docs/adr/FCM_AND_PUSH.md`](adr/FCM_AND_PUSH.md) |
| סקירה כללית | [`ARCHITECTURE.md`](../ARCHITECTURE.md) |

---

*נוצר כמסמך מקביל לקורות חיים — עדכן אם הוספת שירות או שינית שם תיקייה קריטי.*
