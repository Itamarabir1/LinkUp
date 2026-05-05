# מפת תיעוד (Documentation map)

מסמך זה הוא **נקודת כניסה מדורגת**: איפה מחפשים מה, ומה מקור האמת ההנדסי מול הקוד והפריסה. מומלץ לעדכן כאן בעת הוספת מסמך ארכיטקטוני מהותי חדש.

## 1. ניווט מהיר לפי שאלה

| אני צריך… | התחלה כאן |
|-----------|-----------|
| סקירת מוצר + CI + GHCR | [`README.md`](../README.md) |
| ארכיטקטורה רחבה (קישורים לכל התחומים) | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| הרצה מקומית (CMD/Windows), Docker | [`RUN.md`](../RUN.md), [`docs/architecture/DEVELOPMENT.md`](architecture/DEVELOPMENT.md) |
| פריסת production, rollback | [`docs/DEPLOYMENT.md`](DEPLOYMENT.md), [`docs/operations/RUNBOOK.md`](operations/RUNBOOK.md) |
| ניתור, Prometheus, בריאות, Sentry, Better Stack | [`docs/operations/MONITORING.md`](operations/MONITORING.md) (כולל טבלאות מטריקות והערות **wired vs reserved**), [`docs/architecture/API.md`](architecture/API.md) (Health) |
| API endpoints | [`docs/architecture/API.md`](architecture/API.md) |
| סכימת DB, Alembic | [`docs/architecture/DATABASE.md`](architecture/DATABASE.md), [`backend/alembic/README.md`](../backend/alembic/README.md) |
| Outbox, RabbitMQ, DLQ | [`docs/architecture/EVENTS.md`](architecture/EVENTS.md) |
| צ’אט / WS / Redis | [`docs/architecture/REALTIME.md`](architecture/REALTIME.md), [`chat-ws/ARCHITECTURE.md`](../chat-ws/ARCHITECTURE.md) |
| סיכום שיחה (Groq), `task-worker` מול `ai-worker` | [`docs/architecture/AI.md`](architecture/AI.md) |
| התראות, FCM, Brevo | [`docs/architecture/NOTIFICATIONS.md`](architecture/NOTIFICATIONS.md), [`docs/FCM_SYSTEM_SUMMARY.md`](FCM_SYSTEM_SUMMARY.md) |
| Billing, Stripe, idempotency | [`docs/BILLING_REFACTOR_SUMMARY.md`](BILLING_REFACTOR_SUMMARY.md), [`docs/FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md) |
| החלטות ותירוצים (ADR) | [`docs/adr/README.md`](adr/README.md) |
| Frontend (ארכיטקטורה מפורטת) | [`frontend/docs/ARCHITECTURE.md`](../frontend/docs/ARCHITECTURE.md) |
| פרונט — **מה נשאר / backlog** (RQ, a11y, compiler, בדיקות) | [`docs/FRONTEND_UPGRADE_ROADMAP.md`](FRONTEND_UPGRADE_ROADMAP.md) |
| פרונט — אבחון ביצועים (LCP/INP, צ’אנקים) | [`docs/FRONTEND_PERFORMANCE_RUNBOOK.md`](FRONTEND_PERFORMANCE_RUNBOOK.md) |
| סיבות עיצוב / trade-offs שוטפים | [`docs/FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md), [`docs/FUTURE_WORK.md`](FUTURE_WORK.md) |
| עץ תיקיות (snapshot) | [`PROJECT_STRUCTURE.md`](../PROJECT_STRUCTURE.md) |

## 2. אימות מול הריפו (מקור אמת “חי”)

- **Compose — שירותים ופרופילים:** [`docker-compose.yml`](../docker-compose.yml) (`prod`, `compat` ל־`outbox-worker`, וכו’).
- **CI backend — סדר שלבים:** [`.github/workflows/backend-ci.yml`](../.github/workflows/backend-ci.yml) (Ruff → Alembic → `check-migration-head` → pytest RabbitMQ נקודתי → pytest מלא; push ל־`main` בונה תמונות `linkup/backend`, `worker`, `migrate`, `pgbouncer`; בלוק ה-deploy על EC2 מריץ `envsubst` רק ל־**`nginx/nginx.conf`** מ־**`SENTRY_REPORT_URI`** ב־`backend/.env`).
- **Nginx CSP + PgBouncer secrets (מקור אמת):** [`nginx/nginx.conf.template`](../nginx/nginx.conf.template), [`scripts/ops/render-nginx-conf.sh`](../scripts/ops/render-nginx-conf.sh), [`docs/SECURITY_HEADERS.md`](SECURITY_HEADERS.md), [`infrastructure/pgbouncer/userlist.txt.template`](../infrastructure/pgbouncer/userlist.txt.template), [`infrastructure/pgbouncer/entrypoint.sh`](../infrastructure/pgbouncer/entrypoint.sh), סעיף **PgBouncer** ב־[`docs/FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md#pgbouncer).
- **תמונות GHCR בשורש הפרויקט:** [`README.md`](../README.md) (טבלת CI + רשימת repositories).
- **רואטרים בפועל:** [`backend/app/api/v1/api_router.py`](../backend/app/api/v1/api_router.py) (prefix **`/api/v1`**).
- **CI frontend — חוזה OpenAPI:** [`frontend-ci.yml`](../.github/workflows/frontend-ci.yml) → job **`contract-codegen`** (`npm run gen:api` + בדיקת `git diff` על [`frontend/src/api/generated/`](../frontend/src/api/generated/)); **`publish-image`** דוחף **`ghcr.io/.../linkup/frontend:latest`**.
- **Deploy פרונט ל־EC2 (אחרי Frontend CI):** [`deploy-frontend-ec2.yml`](../.github/workflows/deploy-frontend-ec2.yml) — טריגר **`workflow_run`** כש־**Frontend CI** על **`main`** מסתיים ב־**success**; SSH ל־EC2, `docker pull` ל־frontend, **`compose up`** ל־`frontend` + **`nginx --force-recreate`**, smoke ל־`/config.js`.

## 3. מסמכים קצרים / הרחבה

- **AI / סיכום שיחה:** [`docs/architecture/AI.md`](architecture/AI.md) — מקור אמת מלא (שני נתיבי הטריגיר + הגבלות תיעוד).
- **אחסון:** [`docs/architecture/STORAGE.md`](architecture/STORAGE.md) — תקציר; פירוט נוסף ב־`S3_CORS.md` וכו’ לפי הצורך.

## 4. שירותים מחוץ ל-backend

| שירות | תיעוד |
|--------|--------|
| **email-renderer** | [`email-renderer/README.md`](../email-renderer/README.md), workflow **email-renderer-ci** |
| **chat-ws** | [`chat-ws/README.md`](../chat-ws/README.md), **`chat-ws/ARCHITECTURE.md`** |

---

## 5. מגבלות

- **`PROJECT_STRUCTURE.md`** הוא **snapshot** — לא מתעדכן אוטומטית עם כל commit; אל תיחשבו לו למקור חי למספר קבצים.
- בתיעוד “ארוך שנים” (ראיון, Highlights) עלול להישאר ניסוח ישן; **מקור אמת לטריגרים**: קוד (`rg`, IDE) ו־**`DOCUMENTATION_MAP` §2**.

## 6. רשימת בדיקה — שינוי זרימת AI / workers (ניקוי מסיבי, לא תיקון נקודתי)

כשמשנים טריגיר לניתוח צ’אט, Redis, או workers — לעדכן **ביחד** (או להוסיף הפניה צולבת):

1. [`docs/architecture/AI.md`](architecture/AI.md) — מקור האמת לשני הנתיבים  
2. [`docs/architecture/REALTIME.md`](architecture/REALTIME.md) (גם הפסקה הראשונה על DB 0/1 + completion), [`chat-ws/README.md`](../chat-ws/README.md), [`chat-ws/ARCHITECTURE.md`](../chat-ws/ARCHITECTURE.md)  
3. [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) (§8 + טבלאות workers / מטריצת Redis)  
4. [`README.md`](../README.md) (טבלת שירותים + Architecture Decisions אם רלוונטי)  
5. [`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md`](adr/ARCHITECTURE_DECISIONS_BACKEND.md) §15, [`docs/internal/INTERVIEW_TECH_STACK_MAP.md`](internal/INTERVIEW_TECH_STACK_MAP.md) §12  
6. תסריטים: [`docs/internal/VIDEO_SCRIPT_ARCHITECTURE.md`](internal/VIDEO_SCRIPT_ARCHITECTURE.md)

*כשמתעדכנת ארכיטקטורה שחוצה צוותים (למשל workers, compose, GHCR), מומלץ לעדכן גם טבלה §1 במסמך זה.*

---

## 7. רשימת בדיקה — תאימות תיעוד מול קוד (סריקה תקופתית)

לפני merge של שינוי בדומיין או ב-realtime, כדאי לעבור על:

| צעד | מקור אמת |
|-----|----------|
| אילו רואטרים באמת מחוברים | [`backend/app/api/v1/api_router.py`](../backend/app/api/v1/api_router.py) |
| טבלאות HTTP לפי דומיין | [`docs/architecture/API.md`](architecture/API.md) |
| WS ב-FastAPI (נסיעות / מיקום) + נתיבי chat-ws | [`docs/adr/WEBSOCKETS.md`](adr/WEBSOCKETS.md), [`docs/architecture/REALTIME.md`](architecture/REALTIME.md) |
| התראות in-app (REST + `user:{id}:events`, לא רואטר `/notifications`) | [`docs/architecture/NOTIFICATIONS.md`](architecture/NOTIFICATIONS.md) |
| איזה hook בפרונט יושב על איזה WS | [`frontend/src/hooks/`](../frontend/src/hooks/) (`useUserEventStream`, `useRideWebSocket`, `useReconnectingWebSocketState`, …) מול [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) |
