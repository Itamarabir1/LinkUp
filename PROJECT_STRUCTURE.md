# סכמת מבנה הפרויקט – LinkUp

מסמך זה הוא snapshot תיעודי (לא מקור אמת מחייב לקובץ-לקובץ), ועלול לפגר אחרי שינויים בריפו.  
למצב עדכני בזמן אמת עדיף להסתמך על העץ בפועל (`git ls-files` / IDE) ועל מסמכי ארכיטקטורה בשורש (`README.md`, `ARCHITECTURE.md`).

**עדכונים אחרונים בתיעוד:** **פיצול SRP ב־bookings:** קריאות צבירה ב־**`booking_reads_service.py`** (`BookingReadsService`), שידור GPS ב־**`location_service.py`** (`BookingLocationService`), מחזור חיים ב־**`service.py`** (`BookingService`) + ייצוא לאחור; עזרי **Idempotency-Key** ל־join מחיפוש ב־**`ride_join_idempotency.py`** ולצ’אט ב־**`backend/app/domain/chat/message_idempotency.py`** (ADR §25); בפרונט הוק **`useJoinRide.ts`** לצד **`useSearchRides.ts`**. **Circuit Breaker:** מחלקה משותפת **`backend/app/infrastructure/circuit_breaker.py`**; singletons גיאו ב־**`geo/circuit_breaker.py`**; **`brevo_email_cb`** ב־**`backend/app/infrastructure/notifications/circuit_breaker.py`**; מדדי **`geo_circuit_breaker_state`** / **`brevo_circuit_breaker_state`**; **`circuit_breakers`** ב־**`GET /api/v1/health`** — `docs/ENGINEERING_HIGHLIGHTS.md`, `docs/architecture/API.md`, `docs/architecture/NOTIFICATIONS.md`, `docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §20; **`Idempotency-Key`** — `ARCHITECTURE.md`, `docs/architecture/API.md`, ADR §19 (נסיעות) + §25 (צ’אט), `docs/ENGINEERING_HIGHLIGHTS.md` §7ה; **JWT denylist** — ADR §18; שירות **`email-renderer/`**, **`frontend/src/i18n/`**, **`date.ts`**, **`i18nError.ts`**, פונטים ב־CSS Modules; **`EVENTS.md`** — `ride.created` לעומת `ride.created_for_passengers`; ADR §17. עץ התיקיות המפורט למטה עלול עדיין להציג קבצים שהוסרו או הוזזו — השוו לריפו.

---

## שורש הפרויקט (LinkUp/)

```
LinkUp/
├── .git/                          # מאגר Git
├── .github/
│   └── workflows/                 # CI/CD
│       ├── backend-ci.yml
│       ├── chat-ws-ci.yml
│       ├── deploy-ec2.yml         # פריסת EC2 אחרי workflow_run (CI ירוק על main)
│       ├── email-renderer-ci.yml
│       └── frontend-ci.yml
├── .vscode/
│   └── settings.json
├── .gitignore
├── .env.example                   # דוגמה ל-.env בשורש (docker-compose: Postgres/Redis/RabbitMQ)
├── docker-compose.yml             # כולל frontend + nginx עם profile prod
├── README.md
├── RUN.md
├── backend/
├── chat-ws/
├── db/
├── docs/                          # ארכיטקטורה, ADR, ENGINEERING_HIGHLIGHTS, FUTURE_WORK, FRONTEND_UPGRADE_ROADMAP, תסריטי וידאו
├── email-renderer/                # מיקרו-שירות Node — React Email, /render
├── files/                         # מדריכי מיזוג ועזר (לא מקור אמת לקוד)
├── frontend/
└── mobile/
```

---

## backend/

```
backend/
├── .env
├── .env.example
├── .pytest_cache/                 # cache של pytest (לא חלק מקוד המקור)
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   ├── README.md
│   └── v/cache/nodeids
├── alembic.ini
├── Dockerfile
├── Makefile
├── .dockerignore
├── pyproject.toml               # תלויות (מקור); **`uv.lock`** לנעילת גרסאות — אין `requirements.txt` ב-backend
├── README.md
├── load_test.js                   # Grafana k6 — wrapper ל-auth (מפנה ל־k6/scripts)
├── load_test_rides.js             # wrapper ל-rides k6
├── k6/
│   ├── README.md
│   ├── scripts/                   # load_test_auth.js, rides, users, groups, chat, geo, ws
│   └── results/                   # פלטי ריצה (אופציונלי)
├── run-backend.bat
├── run-backend.sh
├── alembic/
│   ├── env.py
│   ├── README.md
│   ├── script.py.mako
│   └── versions/              # רשימת רוויזיות עדכנית: **`docs/architecture/DATABASE.md`** / `uv run alembic history` (לא משבצים כאן את כל הקבצים)
├── app/
│   ├── main.py, admin_config.py, __init__.py
│   ├── admin/setup.py                    # SQLAdmin (optional)
│   ├── api/
│   │   ├── dependencies/                 # auth + service DI (`services.py`, etc.)
│   │   └── v1/api_router.py             # include_router under `/api/v1`
│   ├── core/                             # config, lifespan, middleware, security, exceptions
│   ├── db/                               # models, session, base
│   ├── domain/                           # DDD: typically router + service/crud/schema
│   │   ├── admin, auth, billing, bookings, chat, geo, groups
│   │   ├── notifications, passengers, rides, users
│   │   ├── events/                       # enums, RabbitMQ routing metadata
│   │   ├── scheduled_notifications/
│   │   └── system/                       # outbox_service, maintenance
│   ├── infrastructure/                   # audit, geo HTTP, firebase, RabbitMQ, Redis, S3, metrics
│   │   # see `backend/app/infrastructure/` for dispatcher, Lua rate limits (auth/chat), DLQ tooling
│   └── workers/
│       ├── ai_worker.py, notification_worker.py, task_worker.py
│       ├── outbox_worker.py             # run_outbox_worker (invoked by notification worker)
│       └── tasks/                         # notifications, avatar, scheduled, chat summary/timeout, …
└── tests/                                # api/, domain/, infrastructure/, core_flows/ (+ root tests) — `git ls-files backend/tests`
```

---

## chat-ws/

```
chat-ws/
├── .dockerignore
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── Dockerfile
├── go.mod
├── Makefile
├── README.md
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── auth/
│   │   └── jwt.go
│   ├── config/
│   │   └── config.go
│   ├── hub/
│   │   ├── conn.go
│   │   ├── handler.go
│   │   ├── hub.go
│   │   └── message.go
│   ├── redis/
│   │   └── subscriber.go
│   └── safego/
│       └── safego.go                  # panic recovery for goroutines (RecoverPanic)
```

---

## db/

```
db/
├── schema.sql                 # snapshot ידני / דיבוג; מקור אמת לסכמה בפרודקשן — Alembic ב-backend/
├── scripts/
│   └── check_match_distance.sql
```

**הערה:** לתיאור עמודות וקשרים מעודכן — **`docs/architecture/DATABASE.md`**; להרצת מיגרציות — `backend/alembic/` ו-`backend/README.md`.

---

## docs/

מקור אמת לסכמת DB (טבלאות, אינדקסים, מיגרציות): **`docs/architecture/DATABASE.md`**. סקירה הנדסית (פורטפוליו): **`docs/ENGINEERING_HIGHLIGHTS.md`**. שגיאות API: **`docs/ERRORS.md`**. אבחון ביצועים פרונט: **`docs/FRONTEND_PERFORMANCE_RUNBOOK.md`**. **מפת ניווט מלאה:** **`docs/DOCUMENTATION_MAP.md`**.

```
docs/
├── DOCUMENTATION_MAP.md       # נקודת כניסה + אימות compose/CI
├── ARCHITECTURE.md            # כניסת ארכיטקטורה
├── ENGINEERING_HIGHLIGHTS.md
├── FEATURE_DECISIONS.md
├── DEPLOYMENT.md
├── ERRORS.md
├── FCM_SYSTEM_SUMMARY.md
├── BILLING_REFACTOR_SUMMARY.md
├── FUTURE_WORK.md
├── S3_CORS.md
├── SECURITY_HEADERS.md
├── FRONTEND_PERFORMANCE_RUNBOOK.md   # טריאז' LCP/INP, צ'אנקים (מקושר גם מ-DOCUMENTATION_MAP)
├── architecture/              # API, DATABASE, EVENTS, REALTIME, AI, STORAGE, …
├── adr/
├── operations/                # RUNBOOK, MONITORING
└── internal/                  # ראיון, תסריטי וידאו
```

---

## frontend/

העץ הבא **מצומצם לדוגמה** ואינו משקף את כל `src/` (מודול אדמין, קבוצות, GPS hooks, `context/*` לצ’אט והתראות in-app, וכו’). מקור מעודכן: **`frontend/docs/ARCHITECTURE.md`**.

```
frontend/
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── eslint.config.js
├── index.html
├── nginx.conf
├── package-lock.json
├── package.json
├── README.md
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── dist/                          # build output (לא ב-Git)
├── node_modules/                  # תלויות npm (לא מפורט)
├── public/
│   └── vite.svg
└── src/
    ├── App.css
    ├── App.tsx
    ├── index.css
    ├── main.tsx
    ├── api/
    │   └── client.ts
    ├── assets/
    │   └── react.svg
    ├── components/
    │   ├── Layout/
    │   │   ├── index.tsx
    │   │   └── Layout.module.css
    │   ├── RouteMapModal/
    │   │   ├── index.tsx
    │   │   └── RouteMapModal.module.css
    │   ├── GoogleSignIn.tsx
    ├── config/
    │   └── env.ts
    ├── context/
    │   └── AuthContext.tsx
    ├── pages/
    │   ├── CreateRide.module.css
    │   ├── CreateRide.tsx
    │   ├── Login.module.css
    │   ├── Login.tsx
    │   ├── Messages.module.css
    │   ├── Messages.tsx
    │   ├── MessageThread.module.css
    │   ├── MessageThread.tsx
    │   ├── MyBookings/
    │   │   ├── index.tsx
    │   │   ├── MyBookings.module.css
    │   │   ├── PassengerBookingCard.tsx
    │   │   ├── PassengerBookingsTab.tsx
    │   │   ├── DriverBookingsTab.tsx
    │   │   ├── myBookings.mappers.ts
    │   │   ├── useMyBookings.ts
    │   │   ├── useMyBookingsDriver.ts
    │   │   ├── useMyBookingsPassenger.ts
    │   │   ├── myBookings.types.ts
    │   │   ├── myBookings.constants.ts
    │   │   └── myBookings.utils.ts
    │   ├── MyRequests.module.css
    │   ├── MyRequests.tsx
    │   ├── MyRides.module.css
    │   ├── MyRides.tsx
    │   ├── Notifications.module.css
    │   ├── Notifications.tsx
    │   ├── Profile.module.css
    │   ├── Profile.tsx
    │   ├── Register.module.css
    │   ├── Register.tsx
    │   ├── SearchRides.module.css
    │   ├── SearchRides.tsx
    │   ├── VerifyEmail.module.css
    │   └── VerifyEmail.tsx
    ├── types/
    │   ├── api.ts
    │   └── google-maps.d.ts
    └── utils/
        ├── date.ts
        └── duration.ts
```

---

## mobile/

```
mobile/
├── .env.example
├── .gitignore
├── app.json
├── App.tsx
├── index.ts
├── package-lock.json
├── package.json
├── README.md
├── tsconfig.json
├── assets/
│   ├── adaptive-icon.png
│   ├── favicon.png
│   ├── icon.png
│   └── splash-icon.png
├── node_modules/                  # תלויות npm (לא מפורט)
└── src/
    ├── api/
    │   └── client.ts
    ├── config/
    │   └── env.ts
    ├── context/
    │   └── AuthContext.tsx
    ├── hooks/
    │   └── useGeo.ts
    ├── navigation/
    │   └── AppNavigator.tsx
    ├── screens/
    │   ├── CreateRideScreen.tsx
    │   ├── LoginScreen.tsx
    │   ├── MyRequestsScreen.tsx
    │   ├── MyRidesScreen.tsx
    │   ├── ProfileScreen.tsx
    │   ├── RegisterScreen.tsx
    │   └── SearchRidesScreen.tsx
    └── types/
        └── api.ts
```

---

## .github/workflows/

```
.github/
└── workflows/
    ├── backend-ci.yml
    ├── chat-ws-ci.yml
    ├── deploy-ec2.yml
    ├── email-renderer-ci.yml
    ├── frontend-ci.yml
    └── openapi-contract.yml           # backend↔frontend OpenAPI schema drift detection
```

---

## הערות

- **backend**: שרת API ב‑Python (FastAPI), עם Alembic למיגרציות, workers, ותשתיות (Redis, RabbitMQ, S3, Firebase).
- **email-renderer**: מיקרו-שירות Node.js/Express לרינדור תבניות מייל ב-React Email (`src/emails/components`, `src/emails/templates`, registry + `/render`).
- **chat-ws**: שרת WebSocket ב‑Go בלבד. אחראי על העברת הודעות בזמן אמת בין משתמשים.
- **db**: סכמה (schema.sql) וסקריפטים שימושיים; מיגרציות ב-backend/alembic/.
- **frontend**: אפליקציית ווב ב‑React + TypeScript + Vite.
- **mobile**: אפליקציית מובייל (Expo/React Native) ב‑TypeScript.
- **.github/workflows**: CI — `backend-ci`, `frontend-ci`, `chat-ws-ci`, **`email-renderer-ci`**, **`openapi-contract`** (paths לפי שירות); **`deploy-ec2.yml`** — פריסה ל-EC2 (`workflow_run`).
- **node_modules** (ב‑frontend ו‑mobile) ו־**.venv** (בסביבות Python) לא פורטו – אלה תלויות שנוצרות בהתקנה.
- קבצי **.env** לא נכללו בתיאור מפורש מטעמי אבטחה; הם קיימים לפי .env.example.

*מסמך זה snapshot תיעודי — מתעדכן ידנית; לעץ קבצים חי העדיפו הריפו / IDE.*
