# סכמת מבנה הפרויקט – LinkUp

מסמך זה הוא snapshot תיעודי (לא מקור אמת מחייב לקובץ-לקובץ), ועלול לפגר אחרי שינויים בריפו.  
למצב עדכני בזמן אמת עדיף להסתמך על העץ בפועל (`git ls-files` / IDE) ועל מסמכי ארכיטקטורה בשורש (`README.md`, `ARCHITECTURE.md`).

**עדכונים אחרונים בתיעוד:** **פיצול SRP ב־bookings:** קריאות צבירה ב־**`booking_reads_service.py`** (`BookingReadsService`), שידור GPS ב־**`location_service.py`** (`BookingLocationService`), מחזור חיים ב־**`service.py`** (`BookingService`) + ייצוא לאחור; עזרי **Idempotency-Key** ל־join מחיפוש ב־**`ride_join_idempotency.py`**; בפרונט הוק **`useJoinRide.ts`** לצד **`useSearchRides.ts`**. **Circuit Breaker** לקריאות Google Maps (**`backend/app/infrastructure/geo/circuit_breaker.py`**) + **`circuit_breakers`** ב־**`GET /api/v1/health`** — `docs/ENGINEERING_HIGHLIGHTS.md`, `docs/architecture/API.md`, `docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §20; **`Idempotency-Key`** — `ARCHITECTURE.md`, `docs/architecture/API.md`, ADR §19, `docs/ENGINEERING_HIGHLIGHTS.md` §7ה; **JWT denylist** — ADR §18; שירות **`email-renderer/`**, **`frontend/src/i18n/`**, **`date.ts`**, **`i18nError.ts`**, פונטים ב־CSS Modules; **`EVENTS.md`** — `ride.created` לעומת `ride.created_for_passengers`; ADR §17. עץ התיקיות המפורט למטה עלול עדיין להציג קבצים שהוסרו או הוזזו — השוו לריפו.

---

## שורש הפרויקט (LinkUp/)

```
LinkUp/
├── .git/                          # מאגר Git
├── .github/
│   └── workflows/                 # CI/CD
│       ├── backend-ci.yml
│       ├── chat-ws-ci.yml
│       └── frontend-ci.yml
├── .vscode/
│   └── settings.json
├── .gitignore
├── .env.example                   # דוגמה ל-.env בשורש (docker-compose: Postgres/Redis/RabbitMQ)
├── docker-compose.yml             # כולל frontend + nginx עם profile prod
├── k8s/                           # הגדרות Kubernetes
│   ├── base/
│   ├── backend/
│   ├── chat-ws/
│   ├── frontend/
│   └── infra/
├── README.md
├── RUN.md
├── backend/
├── chat-ws/
├── db/
├── docs/                          # ארכיטקטורה, ADR, ENGINEERING_HIGHLIGHTS, תסריטי וידאו
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
├── celerybeat-schedule
├── Dockerfile
├── Makefile
├── .dockerignore
├── requirements.txt
├── README.md
├── load_test.js                   # Grafana k6 — עומס register/login (ראו backend/README.md)
├── run-backend.bat
├── run-backend.sh
├── alembic/
│   ├── env.py
│   ├── README.md
│   ├── script.py.mako
│   └── versions/
│       ├── add_refresh_token_to_users.py
│       ├── add_ride_distance_duration_columns.py
│       ├── add_route_summary_to_rides.py
│       └── normalize_ride_status_enum.py
├── app/
│   ├── __init__.py
│   ├── admin_config.py
│   ├── main.py
│   ├── admin/
│   │   └── setup.py
│   ├── api/
│   │   ├── dependencies/
│   │   │   ├── auth.py
│   │   │   ├── file.py
│   │   │   └── rate_limit.py
│   │   ├── v1/
│   │   │   ├── api_router.py
│   │   │   └── routers/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── bookings.py
│   │   │       ├── chat.py
│   │   │       ├── geo.py
│   │   │       ├── passengers.py
│   │   │       ├── rides.py
│   │   │       └── users.py
│   │   └── websockets/
│   │       └── notifications.py
│   ├── core/
│   │   ├── config.py
│   │   ├── lifespan.py
│   │   ├── security.py
│   │   ├── exceptions/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── base.py
│   │   │   ├── base_user.py
│   │   │   ├── booking.py
│   │   │   ├── handlers.py
│   │   │   ├── infrastructure.py
│   │   │   ├── notification.py
│   │   │   ├── passenger.py
│   │   │   ├── ride.py
│   │   │   ├── user.py
│   │   │   └── validation.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── https_redirect.py
│   │   │   └── security_headers.py
│   │   └── utils/
│   │       └── validators.py
│   ├── db/
│   │   ├── base.py
│   │   ├── models.py
│   │   └── session.py
│   ├── domain/
│   │   ├── auth/
│   │   │   ├── google_auth.py
│   │   │   ├── schema.py
│   │   │   ├── service.py
│   │   │   └── verification_service.py
│   │   ├── bookings/
│   │   │   ├── booking_reads_service.py
│   │   │   ├── crud.py
│   │   │   ├── enum.py
│   │   │   ├── location_service.py
│   │   │   ├── manifest_mapping.py
│   │   │   ├── model.py
│   │   │   ├── router.py
│   │   │   ├── schema.py
│   │   │   └── service.py
│   │   ├── chat/
│   │   │   ├── __init__.py
│   │   │   ├── ai/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analyzer.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── client.py
│   │   │   │   ├── crud.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── schema.py
│   │   │   ├── calendar_export.py
│   │   │   ├── completion/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── detector.py
│   │   │   │   └── service.py
│   │   │   ├── crud.py
│   │   │   ├── model.py
│   │   │   ├── schema.py
│   │   │   ├── service.py
│   │   │   └── calendar/
│   │   │       ├── __init__.py
│   │   │       ├── builder.py
│   │   │       ├── event.py
│   │   │       ├── exporter.py
│   │   │       └── time_parser.py
│   │   ├── events/
│   │   │   ├── enum.py
│   │   │   ├── model.py
│   │   │   ├── outbox.py
│   │   │   ├── routing.py
│   │   │   └── schema.py
│   │   ├── geo/
│   │   │   ├── processor.py
│   │   │   ├── schema.py
│   │   │   ├── mixins.py
│   │   │   └── utils.py
│   │   ├── notifications/
│   │   │   ├── constants.py
│   │   │   ├── manager.py
│   │   │   ├── channels/
│   │   │   │   ├── email/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── client.py
│   │   │   │   │   ├── renderer.py
│   │   │   │   │   └── templates/
│   │   │   │   │       ├── chat/
│   │   │   │   │       │   └── conversation_summary.html
│   │   │   │   │       ├── driver/
│   │   │   │   │       │   ├── new_ride_request.html
│   │   │   │   │       │   ├── passenger_cancelled.html
│   │   │   │   │       │   └── ride_reminder_driver.html
│   │   │   │   │       ├── passenger/
│   │   │   │   │       │   ├── booking_approved.html
│   │   │   │   │       │   ├── booking_rejected.html
│   │   │   │   │       │   ├── ride_cancelled_by_driver.html
│   │   │   │   │       │   ├── ride_reminder_passenger.html
│   │   │   │   │       │   └── ride_created_for_passengers.html
│   │   │   │   │       └── user/
│   │   │   │   │           ├── password_reset.html
│   │   │   │   │           ├── verify_email.html
│   │   │   │   │           └── welcome.html
│   │   │   │   └── push/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── client.py
│   │   │   │       └── render.py
│   │   │   ├── config/
│   │   │   │   ├── mappings.py
│   │   │   │   └── templates_map/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── email_conf.py
│   │   │   │       └── push_conf.py
│   │   │   ├── core/
│   │   │   │   ├── facade.py
│   │   │   │   ├── handler.py
│   │   │   │   ├── resolver.py
│   │   │   │   └── builders/
│   │   │   │       ├── base.py
│   │   │   │       ├── booking_builder.py
│   │   │   │       ├── chat_builder.py
│   │   │   │       ├── registry.py
│   │   │   │       ├── ride_builder.py
│   │   │   │       └── user_builder.py
│   │   │   ├── providers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── email_provider.py
│   │   │   │   ├── push_provider.py
│   │   │   │   └── websocket_provider.py
│   │   │   └── services/
│   │   │       ├── notification_streamer.py
│   │   │       └── reminder_scheduler.py
│   │   ├── passengers/
│   │   │   ├── ai_search_prompts.py
│   │   │   ├── ai_search_schema.py
│   │   │   ├── ai_search_service.py
│   │   │   ├── crud.py
│   │   │   ├── enum.py
│   │   │   ├── model.py
│   │   │   ├── router.py
│   │   │   ├── ride_join_idempotency.py
│   │   │   ├── schema.py
│   │   │   └── service.py
│   │   ├── rides/
│   │   │   ├── actions.py
│   │   │   ├── cleanup.py
│   │   │   ├── crud.py
│   │   │   ├── enum.py
│   │   │   ├── logic.py
│   │   │   ├── mapper.py
│   │   │   ├── model.py
│   │   │   ├── broadcast.py
│   │   │   ├── repository.py
│   │   │   ├── schema.py
│   │   │   └── service.py
│   │   ├── system/
│   │   │   ├── maintenance_crud.py
│   │   │   ├── maintenance_service.py
│   │   │   └── outbox_service.py
│   │   └── users/
│   │       ├── __init__.py
│   │       ├── crud.py
│   │       ├── model.py
│   │       ├── schema.py
│   │       └── service.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── websocket_bus.py
│   │   ├── events/
│   │   │   ├── dispatcher/
│   │   │   │   ├── base.py
│   │   │   │   ├── evaluator.py
│   │   │   │   └── factory.py
│   │   │   └── publishers/
│   │   │       ├── base.py
│   │   │       ├── rabbitmq.py
│   │   │       ├── redis.py
│   │   │       └── websocket.py
│   │   ├── firebase_core/
│   │   │   ├── firebase-credentials.example.json
│   │   │   └── firebase.py   # production uses FIREBASE_CREDENTIALS_JSON (Model B); local may use FIREBASE_SERVICE_ACCOUNT_PATH
│   │   ├── geo/
│   │   │   ├── circuit_breaker.py   # Circuit Breaker singletons ל-Google Maps APIs
│   │   │   ├── client.py            # Directions + Distance Matrix (GeoClient)
│   │   │   ├── geocode_cache.py
│   │   │   ├── geocoding.py         # GeocodingService (Google HTTP)
│   │   │   └── utils.py
│   │   ├── outbox/
│   │   │   ├── enum.py
│   │   │   ├── model.py
│   │   │   └── repository.py
│   │   ├── rabbitmq/
│   │   │   ├── client.py
│   │   │   ├── consumer.py
│   │   │   ├── supervisor.py
│   │   │   └── topology.py
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   ├── broadcast.py
│   │   │   ├── chat_completion_publish.py
│   │   │   ├── client.py
│   │   │   ├── keys.py
│   │   │   └── pubsub.py
│   │   └── s3/
│   │       ├── client.py
│   │       └── service.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── location/
│   │       ├── __init__.py
│   │       ├── geocoding.py
│   │       ├── location_service.py
│   │       └── routing.py
│   └── workers/
│       ├── main_worker.py
│       ├── outbox_worker.py
│       └── tasks/
│           ├── avatar_tasks.py
│           ├── chat_summary_task.py
│           ├── chat_timeout_task.py
│           ├── fuel_price_task.py
│           ├── maintenance_task.py
│           ├── notification_tasks.py
│           ├── ride_task.py
│           └── scheduled_tasks.py
└── tests/
    ├── __init__.py
    └── test_security.py
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
│   └── redis/
│       └── subscriber.go
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

מקור אמת לסכמת DB (טבלאות, אינדקסים, מיגרציות): **`docs/architecture/DATABASE.md`**. סקירה הנדסית (פורטפוליו): **`docs/ENGINEERING_HIGHLIGHTS.md`**. שגיאות API: **`docs/ERRORS.md`**.

```
docs/
├── ENGINEERING_HIGHLIGHTS.md
├── ERRORS.md
├── FCM_SYSTEM_SUMMARY.md
├── S3_CORS.md
├── architecture/
│   ├── API.md
│   ├── DATABASE.md          # טבלאות, indexes, היסטוריית Alembic
│   ├── DEVELOPMENT.md
│   ├── EVENTS.md
│   └── REALTIME.md
└── ...
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
    └── frontend-ci.yml
```

---

## k8s/

```
k8s/
├── base/
│   ├── namespace.yaml
│   └── kustomization.yaml
├── backend/
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── chat-ws/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
├── frontend/
│   ├── deployment.yaml
│   ├── service.yaml
│   └── kustomization.yaml
└── infra/
    ├── configmap.yaml
    ├── postgres.yaml
    ├── redis.yaml
    ├── rabbitmq.yaml
    └── kustomization.yaml
```

---

## הערות

- **backend**: שרת API ב‑Python (FastAPI), עם Alembic למיגרציות, workers, ותשתיות (Redis, RabbitMQ, S3, Firebase).
- **email-renderer**: מיקרו-שירות Node.js/Express לרינדור תבניות מייל ב-React Email (`src/emails/components`, `src/emails/templates`, registry + `/render`).
- **chat-ws**: שרת WebSocket ב‑Go בלבד. אחראי על העברת הודעות בזמן אמת בין משתמשים.
- **db**: סכמה (schema.sql) וסקריפטים שימושיים; מיגרציות ב-backend/alembic/.
- **frontend**: אפליקציית ווב ב‑React + TypeScript + Vite.
- **mobile**: אפליקציית מובייל (Expo/React Native) ב‑TypeScript.
- **.github/workflows**: CI/CD ל‑backend (Python), chat-ws (Go), frontend (React).
- **k8s**: הגדרות Kubernetes (base, backend, chat-ws, frontend, infra).
- **node_modules** (ב‑frontend ו‑mobile) ו־**.venv** (בסביבות Python) לא פורטו – אלה תלויות שנוצרות בהתקנה.
- קבצי **.env** לא נכללו בתיאור מפורש מטעמי אבטחה; הם קיימים לפי .env.example.

*מסמך זה נוצר אוטומטית לפי מבנה התיקיות בפרויקט.*
