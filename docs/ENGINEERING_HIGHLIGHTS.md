# LinkUp — הדגשים הנדסיים (Portfolio / Senior)

**שם הקובץ:** `docs/ENGINEERING_HIGHLIGHTS.md` (בשורש הפרויקט, תחת `docs/`).

מסמך זה אוסף **במקום אחד** את הפיצ’רים, הטכנולוגיות, הדפוסים וההחלטות שמיועדות ל**סקייל, אמינות ותחזוקה** — כדי להציג את הפרויקט ברמת מומחה.  
*זה סיכום “להצגה”, לא מיפוי כל שורה בקוד; אחרי סקירה מול ה-repo הוכנסו גם workers, AI, FCM, Brevo, Google, **חיזוק auth ועומס מקבילי**, **JWT עם `jti` + denylist ב-Redis אחרי logout**, **Idempotency-Key לבקשת הצטרפות מחיפוש (Redis, Stripe-style)**, **Circuit Breaker in-memory לכל קריאת Google Maps Platform בבקאנד (Geocoding / Directions / Distance Matrix) + חשיפת מצב המעגלים ב־`GET /api/v1/health`**, **k6**, **ריפקטור async משמעותי ב-passengers/bookings/rides**, **ריפקטור ארגון בפרונט**, **מסך אדמין פנימי (React + `/api/v1/admin`)**, **מעבר ארכיטקטוני ל-React Email renderer (Node.js/Express)**, **מדיה: S3 + CloudFront (אופציונלי) ואווטארים ב-prefix גרסתי immutable**, ו**i18n (עברית/אנגלית) + פורמט תאריכים לפי לוקאל + fallbacks לשגיאות API דרך `common:err_*` + איחוד פונטים ב־CSS Modules**.*

**לראיון — מיפוי שורת CV ↔ איפה בקוד:** [`INTERVIEW_TECH_STACK_MAP.md`](INTERVIEW_TECH_STACK_MAP.md).

**לראיון — ניווט לפי נושא + טבלת Why / Alternatives / Trade-offs (מקביל למסמך הזה):** [`INTERVIEW_PLAYBOOK.md`](INTERVIEW_PLAYBOOK.md) · [`FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md).

לפרטים טכניים עמוקים יותר: `../ARCHITECTURE.md`, `ERRORS.md`, `architecture/REALTIME.md`, `architecture/EVENTS.md`, `architecture/DATABASE.md`, `architecture/API.md`, `backend/docs/GOOGLE_OAUTH.md`.

---

## Latest architecture updates

- **SLOs & Error Budgets observability baseline:** metrics surface הורחב מ-backend-only ל-backend + workers (`9091/9092/9093`) עם מדדי domain/reliability (auth, rides, bookings, billing, RabbitMQ, outbox, geo cache/circuit-breaker, S3, AI). זה מאפשר להגדיר SLOs רשמיים (availability/latency/reliability) ולנהל release decisions לפי error-budget consumption במקום לפי אינטואיציה.
- **RabbitMQ PR1 reliability guardrails:** consumer runtime now includes supervision + draining states (`RUNNING -> DRAINING -> STOPPED`) and queue-scoped `x-death` parsing for retry observability. Workers run long-lived loops through `run_supervised` with bounded retries (`max_retries`) to prevent silent infinite crash loops.
- **RabbitMQ PR2 topology hardening:** messaging path split to role-specific clients — `rabbit_client` (API publish), `outbox_rabbit_client` (Outbox publish), `worker_rabbit_client` (worker consume/scheduler). Worker consumers share one worker connection but run isolated channels per queue; queue behavior moved to centralized `QueueSpec` (`backend/app/infrastructure/rabbitmq/topology.py`).
- **RabbitMQ PR3 pure DLX/TTL retry:** manual republish retry loop removed from worker path. Retry now broker-native (`retry_exchange` + `<queue>.retry` with `x-message-ttl`) and attempt counting uses queue-scoped `x-death`; workers only `nack(requeue=False)` for transient failures and route terminal failures to queue DLQ.
- **RabbitMQ PR4 DLQ operability:** `notification-worker` now runs periodic DLQ depth monitoring (`run_dlq_monitor`) with warning/critical thresholds and structured logs for early detection of stuck consumers/poison traffic.
- **RabbitMQ PR5a tests in CI:** נוספו בדיקות ייעודיות ל-reliability path (`backend/tests/infrastructure/test_rabbitmq_reliability.py`) ונוספה ריצתן המפורשת ל-`backend-ci` לפני ריצת כלל הטסטים.
- **RabbitMQ PR5b replay tooling:** נוסף כלי אופרטיבי `scripts/ops/rabbitmq-dlq-replay.py` ל-replay מבוקר של הודעות DLQ חזרה לתור הראשי, עם `--queue`, `--limit`, ו-`--dry-run`.
- **PgBouncer (production-ready, Compose internal):** נוסף service ייעודי `pgbouncer` (transaction pooling) בין `backend`/workers לבין `db`, ללא חשיפת פורט חיצוני. כל שירותי runtime (`backend`, `notification-worker`, `task-worker`, `ai-worker`, `outbox-worker`) מחוברים דרך `POSTGRES_HOST=pgbouncer`; `migrate` נשאר direct ל-`db` כדי למנוע friction ב-DDL/migrations. נוספה התאמת דרייבר ב-`session.py`: `connect_args={"statement_cache_size": 0}` עבור asyncpg + PgBouncer. בעקבות בעיות entrypoint ב-images ציבוריים, ה־service עבר ל־custom image (`infrastructure/pgbouncer/Dockerfile`) עם control מלא על `pgbouncer.ini`.
- **Redis HA with Sentinel (Compose-ready):** טופולוגיית Redis עברה ל-`redis-primary` + `redis-replica` + `redis-sentinel`. שירותי Python עובדים ב-`redis.asyncio.Sentinel` עם fallback ל-URL רגיל (dev), ו-`chat-ws` משתמש ב-`go-redis` `NewFailoverClient`. `REDIS_HOST=redis` נשמר כ-alias ל-master כדי לא לשבור קונבנציה קיימת, ו-`REDIS_SENTINEL_HOST` מפעיל את נתיב ה-HA.
- **Backend CD rollout on single EC2 (low-downtime):** pipeline של `backend-ci` מבצע גם deploy אוטומטי ב-push ל-`main` דרך SSH (`appleboy/ssh-action`), עם image tags של `latest` + `sha`, rollout ל-backend (`docker compose up -d --no-deps backend`), health gate על `/api/v1/health`, ו-rollback אוטומטי לתג קודם במקרה כשל.
- **Billing (Stripe) — domain מלא עם hardening ברמת production:** דומיין חדש `billing` (model/schema/crud/service/router), endpointים `checkout/status/payments/webhook`, אינטגרציה ל-`users` (`stripe_customer_id`, `is_premium`, `premium_since`) ומיגרציה ייעודית **013**. הוקשח בסטנדרט סניור: **`PaymentStatus` enum** במקום string חופשי, **idempotency דו-שכבתי** (`stripe_event_id` + `stripe_payment_intent_id`), מיפוי **`IntegrityError` → `PaymentAlreadyExistsError`**, אימות חתימת webhook fail-closed (חסר `Stripe-Signature` → שגיאה מיידית), וקריאות Stripe עטופות `asyncio.to_thread` למניעת חסימת event loop.
- **Google Maps — Circuit Breaker (שלושה מעגלים נפרדים):** מימוש in-memory ב־**`backend/app/infrastructure/geo/circuit_breaker.py`** — singletons **`google_geocoding_cb`**, **`google_directions_cb`**, **`google_distance_matrix_cb`** (מצבים `closed` / `open` / `half_open`; סף כשלונות + timeout התאוששות). **`GeocodingService`** ו־**`GeoClient`** בודקים **`allow_request()`** לפני קריאת HTTP; הצלחה/כשל מעדכנים את המעגל — כשהמעגל **OPEN**, אין קריאות ל-Google (fail-fast: `None` / `[]` לפי הזרימה). **`GET /api/v1/health`** מחזיר אובייקט **`circuit_breakers`** עם שמות המצבים — **אינפורמטיבי בלבד**; **`status`** (`healthy` / `unhealthy`) נקבע רק מ־**database**, **redis**, **rabbitmq** (לא ממצב Google). פירוט: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §20**, **`docs/architecture/API.md`** (Health).
- **Idempotency-Key ל־`POST …/passengers/request-ride-from-search`:** כותרת אופציונלית; Redis **`SET NX`** + fingerprint (SHA-256) על גוף קנוני; מטמון **רק 201**; **409 + Retry-After** בזמן עיבוד; **422** על `idempotency_key_mismatch`; שגיאת דומיין → מחיקת נעילה; **fail-open** בלי Redis. **בקאנד:** עזרים ב־**`ride_join_idempotency.py`**, ראוטר דק. **פרונט:** **`useJoinRide`** מחזיק **`idempotencyKeyRef`** — מפתח יציב לכל ניסיון הצטרפות (איפוס אחרי הצלחה); נקרא מ־**`useSearchRides`**. פירוט: **§7ה**, **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §19**, `passengers.ts` + **`useJoinRide.ts`** / `useSearchRides.ts`.
- **JWT access-token revocation (Redis denylist):** כל access כולל **`jti`**; **`POST /auth/logout`** עם Bearer מוסיף `denylist:{jti}` עם TTL עד `exp`; HTTP dependencies וגם `get_current_user_ws` בודקים denylist בזמן handshake; **fail-open** אם Redis לא זמין. פירוט: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §18**, **`ARCHITECTURE.md`** (Key Patterns / Security), **סעיף 7ד** למטה.
- **Prometheus + Grafana monitoring:** backend חושף `GET /metrics` דרך `prometheus-fastapi-instrumentator`; ב-Compose נוספו שירותי `prometheus` ו-`grafana` תחת profile `monitoring`, עם provisioning מוכן + dashboard בסיסי ל-HTTP (`rate`, `p95`, `5xx`, `in_progress`).
- **Passenger match emails documented end-to-end:** Outbox publishes **`ride.created`**; `notification_tasks.handle_ride_created` runs `find_passengers_for_ride_notification`; per-match notification uses internal event **`ride.created_for_passengers`** (not a second Rabbit routing key). See §6.4 below and **`architecture/EVENTS.md`** (Ride section).
- **WebSocket notifications unified via `chat-ws`**: user refresh/domain events are pushed on the existing chat socket (`user:*:events`), reducing concurrent client WebSocket connections.
- **Outbox dispatch improved**: LISTEN/NOTIFY flow is now primary, with safe fallback behavior to avoid fixed-interval-only polling.
- **Worker split completed**: `notification-worker`, `task-worker`, `ai-worker` each has dedicated runtime responsibilities and K8s HPA policies.
- **DB pool caps per worker**: explicit `DB_POOL_SIZE` + `DB_MAX_OVERFLOW` were tuned per worker to keep total PostgreSQL connections in a safe range.
- **Redis reconnect resilience**: reconnect retry strategy now uses exponential backoff for long-lived pub/sub channels.
- **Google Maps resilience**: קריאות Geocoding / Directions / Distance Matrix עם **timeouts** ב־`httpx`; **Circuit Breaker** נפרד לכל API למניעת storm כשספק הרשת/Google לא יציב; ב־reverse geocode — HTTP **429** מזוהה ככשלון במעגל ונזרקת **`InfrastructureError`** (`error_code` **`GEO_SERVICE_UNAVAILABLE`**) — פורמט אחיד ב־**`docs/ERRORS.md`**.
- **Chat reliability/UX**: missed messages are fetched after reconnect (`after=message_id`), and read receipts now use a DB-level message cursor (`last_read_message_id`) so `✓✓` renders correctly on all outgoing messages up to the partner's read position.
- **Chat inbox N+1 fix + index hardening**: `list_my_conversations` הריצה `get_last_message` + `has_unread_messages` לכל שיחה בנפרד (~3N קריאות). הוחלפה ב-`get_inbox_aggregates` (`chat/crud.py`) — 3 aggregate queries + מיזוג בזיכרון, **4 קריאות קבועות**. נוסף `__table_args__` ב-`Message` model עם `Index("idx_messages_sender_id", "sender_id")` להתאמה ל-migration 012. פירוט: [FEATURE_DECISIONS.md — Chat inbox N+1](FEATURE_DECISIONS.md#chat-inbox-n1).
- **Task scheduler safety**: `task-worker` is fixed to a single replica to prevent duplicate scheduled task publishing.

---

## 0א. יציבות ופרודקשן — בעיה / החלטה / trade-off (סיכום)

סיכום ממוקד לראיון; פירוט טכני: **§7ד**, **§7ה**, **Latest updates**, **`ARCHITECTURE.md`**, ADR **§18–§21**.

### Idempotency-Key — `POST …/request-ride-from-search`

| | |
|--|--|
| **בעיה** | לחיצה כפולה במובייל או retry רשת יוצרות שתי הזמנות לאותה נסיעה. |
| **החלטה** | כותרת אופציונלית **`Idempotency-Key`** (UUID); Redis **`SET NX`** לנעילה פר-משתמש+מפתח; **SHA-256** על גוף קנוני — אי-התאמה → **422**; נשמרת רק תשובת **201** (מוסכמת Stripe); שגיאת דומיין → מחיקת נעילה; **fail-open** אם Redis למטה. בקאנד: **`ride_join_idempotency.py`**. פרונט: **`idempotencyKeyRef`** ב-**`useJoinRide`** (מ־**`useSearchRides`**). |
| **Trade-off** | בלי Redis אין dedup; זמינות מועדפת על idempotency קשיח ברגעי תקלה קצרים. |

### Circuit Breaker — Google Maps (בקאנד)

| | |
|--|--|
| **בעיה** | timeout ארוך (למשל 15s) × בקשות מקבילות = סיכון ל-exhaustion של workers/threads כש-Google איטי. |
| **החלטה** | שלושה **singletons** in-memory (**Geocoding**, **Directions**, **Distance Matrix**); **CLOSED → OPEN** (אחרי סף כשלונות) → **HALF_OPEN** (אחרי ~60s) → **CLOSED**; כש-**OPEN** — ללא קריאת HTTP (התנהגות דומה ל-timeout); מצב ב-**`GET /api/v1/health`** (`circuit_breakers`) **בלי** לשנות **`status`** הכללי; **fail-open** בתוך לוגיקת המעגל. |
| **Trade-off** | מצב לא משותף בין מופעים (restart מאפס); לא מיושם על S3 / Groq / Brevo — שם async+boto3, tenacity, או worker async. |

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
| **ops hardening (חדש)** | `userlist.txt` לא נשמר ב-repo: מייצרים מ-`userlist.txt.template` בזמן deploy (`envsubst` + `chmod 600`), rebuild/restart ל-`pgbouncer` לפני rollout של backend, ו-wait health מפורש ל-`linkup_pgbouncer`. |

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
| **נוסעים / התראות חיפוש** | חיפוש **`GET …/passenger/passengers/search-rides`** — ללא שורת DB; **שמירת בקשה + התראה** — **`POST …/passengers/`** עם `is_notification_active`, `group_id` אופציונלי; בעת יצירת נסיעה — worker מתאים בקשות פעילות (`find_passengers_for_ride_notification`) |
| **הזמנות** | בקשה, אישור/דחייה, race-safe (locks); **`POST …/request-ride-from-search`** — **Idempotency-Key** אופציונלי (Redis) נגד כפילות מלחיצה כפולה / retry |
| **צ’אט** | הודעות real-time, typing, נראות (online / last seen), **unread** (Redis→WS), קריאת שיחה; **DB-level read cursor** (`last_read_message_id`) ל-read receipts על כל ההודעות היוצאות; **Zod** על הודעה נכנסת ב־WS — `ChatMessageSchema` + מיפוי מפורש ל־`MessageResponse` ב־`processChatWebSocketMessage` |
| **קבוצות** | יצירה, **קוד הזמנה** Base62 (8 תווים, `secrets`), יצירה עם **`flush` + retry על `IntegrityError`** רק ל־duplicate על `invite_code`, **`commit`** אחד לקבוצה + חבר admin יוצר; אחרי כשלונות חוזרים — `LinkUpError` **`INVITE_CODE_GENERATION_FAILED`** (`app/domain/groups/crud.py`) |
| **AI** | סיום שיחה → ניתוח (Groq) → שמירה + התראות; בנוסף free-text parsing לנסיעות (`ai-parse-search`) עבור SearchRides (נוסע) ו-CreateRide (נהג, עם כללי זמן מחמירים יותר) |
| **התראות** | מייל (**Brevo**) עם רינדור HTML דרך **email-renderer (React Email)**, Push (**FCM** — מהשרת רק מפת `data` ב־FCM, בלי שדה `notification` של Firebase; בחזית **Toast קופץ + צליל**, ברקע התראת מערכת דרך SW), in-app |
| **משתמשים** | JWT (+ **`jti`**) + Refresh ב-DB; **`POST /auth/logout`** מנקה refresh ומבטל מיידית את ה-access הנוכחי דרך **Redis denylist**; **כניסה עם Google** (OAuth / `id_token`), אווטאר (S3 + worker; **קריאה:** CloudFront כשמוגדר או presigned); שדה **`is_admin`** לגישה ל־`/api/v1/admin/*` |
| **אדמין / תפעול** | ממשק ווב **`/admin`** (מודול `features/admin`): סטטיסטיקות, בריאות, משתמשים (הפעלה/הרשאת אדמין), נסיעות (ביטול), קבוצות, Outbox (requeue), lookup; **lazy routes**, מעטפת **דסקטופ** (ללא drawer מובייל), **`AdminRoute`** מינימלי (`is_admin` מ־AuthContext); אישור לפני מוטציות, toasts; בקאנד **`get_current_admin_user`** + לוג `[admin_audit]` — **`ADMIN_DASHBOARD.md`** |
| **מפות** | Google: **Geocoding**, **Directions**, **Distance Matrix**, **Maps JS**; geocoding הוא **Google-only** עם cache ב-Redis (24h); בבקאנד — **Circuit Breaker** נפרד לכל שלושת ה-APIs של Platform + מצב ב־**`/api/v1/health`** |
| **GPS בזמן אמת** | מיקום נהג לנוסעים, מיקום נוסעים לנהג (ערוצי Redis נפרדים + WS). **פרונט:** POST מותאם ב־throttle (~1.5s), `maximumAge: 0` לשידור, `useMapMarker` — יצירת marker פעם אחת ועדכון מיקום בלבד (בלי ריצוד), מפת Google. **Zod** על פריימי WS בכניסה — `frontend/src/types/wsEvents.ts`. פירוט: `docs/architecture/REALTIME.md`. |
| **תזכורות + אירועי משתמש ב-WS** | טבלת **`scheduled_notifications`** (Alembic 008) במקום דגל `reminder_sent` על rides/bookings; `ReminderScheduler` + handler. פרסום: **`publish_ride_event`** (broadcast/DB0); **`publish_user_event`** דרך **`redis_chat_pubsub`** / `REDIS_CHAT_URL` (DB1, כמו chat-ws) ל-`user:{id}:events`. **chat-ws** נרשם ל-`user:*:events`; **פרונט:** `useUserEventStream` + `HistorySection` / מסכי My Rides & Bookings; טיפוסי **`Booking`** בפרונט ללא `reminder_sent` (יישור Phase 9). |
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
| 5 | **Geocode cache (Redis, 24h)** | `geocode_cache` (Redis) + `GeocodingService` (Google) | כתובת→קואורדינטות עם cache fail-open (חוסך קריאות חיצוניות חוזרות) |
| 6 | **OSRM** (דוגמה ציבורית) | קבוע `OSRM_URL` ב-`GeoClient` | **לא** בשימוש בזרימת `fetch_raw_routes` הנוכחית (שם רק Google); נשאר כתשתית אפשרית. |

**כניסה עם Google (לא מפות):** **OAuth / Identity** — `GOOGLE_CLIENT_ID`, ראה `backend/docs/GOOGLE_OAUTH.md`.

**לסיכום לראיון:** “במפות יש לי **ארבעה APIs של Google Platform** — Geocoding (כולל reverse), Directions, Distance Matrix, ו-JavaScript למפה בדפדפן; geocoding הוא **Google-only** עם cache ב-Redis; מפתח Maps נפרד מ-OAuth של Login.”

---

## 2א. Workers: מה רץ כל הזמן ומה לפי זמן

תהליכי ה-worker פוצלו לפי אחריות: **`notification-worker`**, **`task-worker`**, **`ai-worker`**.

### רצים כל הזמן (כל עוד ה-worker חי)

| רכיב | תפקיד |
|------|--------|
| **`notification-worker`** | Outbox LISTEN/NOTIFY + fallback polling, consumer ל-`notifications_queue` (מייל+FCM+user refresh). |
| **`task-worker`** | consumers ל-`avatar_upload_queue` ו-`scheduled_tasks_queue`, plus scheduled publisher loop כל ~**60 שניות**. |
| **`ai-worker`** | מאזין ל-`chat:completion:*` (Redis DB 1), מפעיל ניתוח **AI (Groq)** ושומר תוצאות ל-DB. |

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
| **משתמש מקליד** | הפרונט שולח ב-WebSocket `typing_start` (בדרך כלל עם throttle). כשמפסיקים — `typing_stop` (למשל אחרי שליחה או blur). **chat-ws** מפרסם ל-Redis `chat:typing:*` והמנוי מעביר לאותו conversation לצד השני — **בלי** לגעת ב-DB. זה **אפhemeral** ומתאים למאות אלפי אירועים קצרים. |
| **משתמש מחובר** | בפתיחת WS: Go שם `presence:{user_id}` ומפרסם **`user:online`** → **`user_online`** ב-WS. בכניסה לשיחה: **קריאה אחת** ל-`GET /presence/{partner_id}` לטעינת מצב ראשוני. |
| **התנתקות (Disconnect)** | Go **מפרסם** `user:offline` → **`user_offline`** ב-WebSocket. במקביל debounce ל-PATCH last-seen (`last_active_at`). |

---

## 5. Real-time נוסף (לא צ’אט)

- **עדכוני נסיעה**: WS ב-FastAPI + Redis Pub/Sub; **מקור אמת לשמות ערוצים** — `app/infrastructure/redis/keys.py` (`get_ride_channel` וכו'). **נקודת כניסה אחת לשידור אירועי נסיעה** — `publish_ride_event` ב־[`app/infrastructure/redis/publisher.py`](../backend/app/infrastructure/redis/publisher.py) (אירועים כמו `RIDE_STARTED` / `RIDE_ENDED` / `RIDE_CANCELLED`). חיבור ל-`/rides/ws/{ride_id}` דורש `?token=JWT` (כמו שאר ה-WS ב-backend).
- **מיקום נהג / נוסעים**: ערוצים נפרדים (`booking_*`, `ride_*:passenger_locations`) + WS ייעודיים — הפרדת עומס ולוגיקה.
- **פרונט (WS)**: **`useRideWebSocket`** — hook גנרי עם reconnect; **`useDriverLocation`** / **`usePassengerLocations`** — reconnect אוטומטי אחרי ניתוק; **`MyRides.tsx`** — מאזינים לערוץ נסיעה עם אותו חוזה JSON. כשנהג לוחץ **התחל נסיעה**, הנוסע רואה מיד את אפשרות **שתף מיקום** (רענון רשימה דרך אירועי סטטוס).
- **אימות JSON (Zod)**: סכימות מרוכזות ב-**`frontend/src/types/wsEvents.ts`** — `RideEventSchema`, `DriverLocationEventSchema`, `PassengerLocationEventSchema`, **`ChatPresenceEventSchema`** (discriminated union: `user_online` / `user_offline` / `typing_*` / `unread_count`). ב-`onmessage` משתמשים ב-**`safeParse`**; פריימים לא צפויים → `console.warn` ודילוג (בלי לשבור את הלולאה). שימוש ב-**`useRideWebSocket`**, **`useDriverLocation`**, **`usePassengerLocations`**, **`MyRides`**, **`processChatWebSocketMessage`**.

---

## 6. סינכרוני מול אסינכרוני + RabbitMQ

במערכת משולבים שני עולמות: **הלקוח מחכה לתשובה (סינכרוני לחוויית משתמש)** מול **עבודה שמתבצעת אחרי שהבקשה נסגרה (אסינכרוני)** — כדי לא לחסום את ה-API ולא לאבד משימות.

### 6.1 מה סינכרוני ומה אסינכרוני (דוגמאות)

| סינכרוני (הלקוח מקבל תשובה מיד / בזמן הבקשה) | אסינכרוני (ממשיכים ברקע; הלקוח לא מחכה) |
|-----------------------------------------------|------------------------------------------|
| **REST**: login, שליחת הודעת צ’אט (POST), אישור הזמנה, חיפוש נסיעות | **מייל / Push** אחרי אירוע עסקי — דרך Outbox → RabbitMQ → consumer |
| **תשובת 200** אחרי commit ל-DB (והפעלת publish ל-Redis לצ’אט) | **עיבוד אווטאר** (S3 resize) — נכנס לתור, ה-API רק מחזיר “התקבל” |
| **GET /presence** ב-chat-ws (online + last_seen מ-DB דרך backend) | **ניתוח AI לשיחה** — Redis completion + worker |
| **PATCH last-seen** — נקרא מה-worker ב-Go אחרי disconnect (לא מהדפדפן של המשתמש המנותק) | **משימות מתוזמנות** (תזכורות, chat timeout, וכו’) — RabbitMQ `scheduled` |
| | **Redis Pub/Sub** — publish לא “מחכה” למנויים; מי שלא מחובר לא מקבל — זה push חד-כיווני |

**עקרון**: דברים שחייבים **עקביות עם DB** (למשל “שמרנו הזמנה”) נשארים בטרנזקציה. דברים ש**יכולים להיכשל זמנית** (מייל, חיצוני, כבד) — **מחוץ** לטרנזקציית ה-HTTP, דרך תורים.

### 6.2 RabbitMQ — תפקיד במערכת

- **לא** כל בקשה עוברת ב-RabbitMQ. ה-API מדבר ישירות עם Postgres / Redis.
- **Outbox-worker** קורא `outbox_events` (PENDING) ו**מפרסם** ל-RabbitMQ לפי routing (user / ride / booking / tasks / scheduled).
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
| **Circuit Breaker (Google Maps)** | שלושה מעגלים in-memory נפרדים ל־Geocoding / Directions / Distance Matrix — מגן על התלות החיצונית ועל העומס כש-Google לא זמין; מצב ב־`/api/v1/health` (**לא** משפיע על readiness). ADR **§20**. |
| **DDD** | דומיינים מבודדים (rides, bookings, chat, …) — קל להרחבה וטסטים. |
| **Pessimistic locking** | אישור/ביטול הזמנה תחת `SELECT FOR UPDATE` — מונע race ו”כפל” לוגיקה תחרותית על אותה נסיעה. |
| **Async SQLAlchemy 2.0 migration** | זרימות ליבה בדומיינים passengers/bookings/rides עברו ל-`AsyncSession` + `select/execute`; פעולות sync נשמרו רק למקטעים שדורשים locking/transactional guarantees. |
| **Chat inbox — aggregate query (N+1 fix)** | `get_inbox_aggregates` (`chat/crud.py`) — 3 שאילתות `func.max` מאוגדות לכלל השיחות במקום `get_last_message` + `has_unread_messages` per-row; מ-~3N ל-4 קריאות קבועות ללא תלות בגודל ה-inbox. פירוט: [FEATURE_DECISIONS.md — Chat inbox N+1](FEATURE_DECISIONS.md#chat-inbox-n1). |
| **JWT קצר + Refresh ב-DB + `jti` + Redis denylist** | אבטחה; refresh נמחק ב-logout; access הנוכחי נחסם מיידית עד `exp` (TTL על `denylist:{jti}`). |
| **Idempotency-Key (Redis, `SET NX`)** | `POST …/request-ride-from-search` — מניע duplicate booking; מטמון **201** בלבד; **§7ה**. |
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
| **רשת / חיצוני** | **Timeouts** ל-Google Geocoding / Directions / Distance Matrix; **Circuit Breaker** נפרד לכל API (fail-fast כשהמעגל OPEN); טיפול ב-**429** ב-reverse geocode עם הודעת דומיין; debounce **last-seen** + ביטול ב-reconnect — לא מציפים DB ולא מעדכנים “offline” בטעות. |
| **תשתית** | **`pool_pre_ping`**, **`pool_timeout`**, **`pool_recycle`** — מאגר DB עמיד יותר; **rate limit** על register + login/refresh; **FCM** — טוקן לא תקף מטופל (איפוס / דילוג). |
| **chat-ws (Go)** | `if redisClient == nil` לפני פעולות; **select default** על ערוץ Send; לקוחות Redis נפרדים ל-`user:offline` ול-`user:online` שלא ייתקעו עם `PSubscribe` של הצ’אט. |
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
| **בדיקת עומס (k6)** | סקריפט **`backend/load_test.js`** — register + login לכל איטרציה. | מאמת end-to-end את השילוב: API, DB pool, Redis (rate limit), validation. **דוגמה למדידה לוקאלית:** 10 VU למשך 30s, ~150 איטרציות, **שיעור שגיאות HTTP 0%**, p95 register ~413ms / login ~363ms (תלוי חומרה וסביבה). |

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

**פרונט:** [`requestRideFromSearch`](../../frontend/src/api/passengers.ts) מקבל מפתח אופציונלי; **[`useJoinRide`](../../frontend/src/pages/SearchRides/useJoinRide.ts)** (נקרא מ־**[`useSearchRides`](../../frontend/src/pages/SearchRides/useSearchRides.ts)**) יוצר **`crypto.randomUUID()`** פעם אחת לכל ניסיון הצטרפות (**`idempotencyKeyRef`**), מעביר ל-API, **מאפס אחרי הצלחה**, ומשאיר את המפתח אחרי שגיאה ל-retry עם אותו מפתח.  
ADR: **`docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` §19**.

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

---

## 8. AI וצ’אט “חכם”

- סיום שיחה → publish ל-`chat:completion:*` על Redis DB 1.
- **ai-worker** (`run_chat_completion_redis_listener`) מאזין, קורא ל-**Groq** (Llama), שומר תוצאות; אפשר המשך דרך outbox (התראות וכו’).
- ייצוא **iCal** ו-API לניתוח — ב-backend בלבד (לא ב-Go).

### FCM + מייל (איפה בקוד)

- **FCM (Backend)**: `app/domain/notifications/channels/push/client.py` — `messaging.Message` עם **`data` בלבד** (ללא `notification`), כולל `title` ו־`body` כמחרוזות + שדות metadata נוספים; `push_provider` שולח רק אם יש `fcm_token`; טיפול בטוקן לא תקף.
- **FCM (Frontend)**: `frontend/src/services/fcm.ts` — הרשאות, רישום SW, `getToken` + `PATCH /users/fcm-token`; **`cleanupFCM()`** מבטל `onMessage`. **AuthContext** — `initFCM()` אחרי login / Google / hydrate אם הרשאה `granted`; ב־logout: `patchFcmToken(null)` (בזמן JWT תקף) → `cleanupFCM()` → `logoutSession` → `clearTokens`. Toast גלובלי ב־**`App.tsx`** (`NotificationToast`). תפריט פרופיל: הפעלת התראות דרך **`useLayoutShell`**. בחזית `onMessage` → `title`/`body` מ־**`payload.data`** → Toast + צליל; `firebase-messaging-sw.js` — **`push`** → `showNotification` ברקע. פירוט: **`docs/FCM_SYSTEM_SUMMARY.md`**.
- **מייל**: **Brevo** דרך `EmailClient` / `email_provider`, עם רינדור HTML דרך שירות ייעודי **`email-renderer`** (Node.js + Express + React Email). ה-backend שולח `template + props` ל-`POST /render` (`EMAIL_RENDERER_URL`), מפת התבניות מנוהלת ב-PascalCase ב-`email_conf.py`, ו-registry בצד renderer כולל fail-fast validation כדי ליפול ב-startup אם תבנית חסרה.

---

## 9. DevOps ופריסה

- **Docker Compose**: healthchecks (כולל **backend** על `/api/v1/health`), סיסמת Redis, volumes ל-RabbitMQ ו-Postgres; שירות **`migrate`** (`alembic upgrade head`, `restart: no`) לפני **backend** וכל ה-workers; שירותי פיתוח (`db`, `redis`, `rabbitmq`, `migrate`, `backend`, `notification-worker`, `task-worker`, `ai-worker`, `chat-ws`) ב־`docker compose up -d`; **frontend** סטטי + **nginx** באותו `docker-compose.yml` עם `profiles: ["prod"]` — סטאק מלא על פורט 80 עם `docker compose --profile prod up -d --build`, **nginx** אחרי **backend** ב־`service_healthy`. קובץ שירות Firebase נטען מ־host ל־**backend** ול־**notification-worker** (volume read-only; `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env`) — נדרש ל־FCM מה־worker. **פריסה בלי Compose** (למשל image בלבד / K8s): להריץ מיגרציה כ־Job או שלב init נפרד — לא מוטמע ב־`CMD` של image ה-production.
- **`.env` כפול לפי תפקיד:** `.env` **בשורש** (מ־`.env.example`) — רק credentials ש־Compose צורך להקמת Postgres / Redis / RabbitMQ; **`backend/.env`** — כל הגדרות הבקאנד. חייב **יישור** (סיסמאות DB/Redis/RabbitMQ) בין הקבצים. אחרי **שינוי `backend/.env`** — לרענן משתנים בקונטיינר: `docker compose up -d --force-recreate backend` (**לא** מספיק `restart` בלבד — ה-env נצרך בעת יצירת הקונטיינר).
- **גרסאות תמונות קבועות** (לא `latest` בשירותים קריטיים) — builds חוזרים.
- **K8s**: deployment ל-`chat-ws` עם env (למשל `BACKEND_URL`) ל-worker של last-seen.

---

## 10. איך להשתמש במסמך הזה בפורטפוליו

- בקורות חיים / לינקדאין: “Real-time chat (מקליד / מחובר / disconnect עם debounce), Go + Redis, Outbox+RabbitMQ, סינכרון מול אסינכרון, PostGIS”.
- בראיון: **סעיף 4** + **5** (real-time נסיעות + Zod) + **6** + **0א** (סיכום בעיה/החלטה/trade-off) + **7ג** (auth בעומס) + **7ד** (JWT denylist) + **7ה** (Idempotency-Key) + **7ב** (defensive) + **Latest architecture updates** (Circuit Breaker Google Maps) + **12** + **13** + **14** (פרונט).

---

## 11. צ’ק-ליסט — מה מכוסה במסמך

| נושא | מכוסה |
|------|--------|
| התראת נוסע על נסיעה חדשה (Outbox `ride.created` → handler → מייל) | **סעיף 6.4** + `architecture/EVENTS.md` |
| מקליד / מחובר / disconnect | סעיף 4 |
| סינכרון / אסינכרון + RabbitMQ | סעיפים 6, **6.4** |
| Workers רצים תמיד vs מתוזמנים | סעיף 2א |
| AI (Groq / Llama) | סעיפים 2, 8 |
| FCM | סעיפים 1, 2, 8 + **`docs/FCM_SYSTEM_SUMMARY.md`** |
| מייל Brevo | סעיפים 1, 2, 6, 8 |
| כניסה עם Google | סעיפים 1, 2, 7א |
| אבטחה + rate limit + OTP + מאגר DB + enumeration + auth בעומס + JWT denylist + Idempotency booking | סעיפים 3, 7, 7א, **0א**, **7ג**, **7ד**, **7ה**, 7ב, 12 |
| ריפקטור פרונט (API, context, lazy, בדיקות) | **סעיף 14** + `frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md` |
| Zod, WebSocket (נסיעות/מיקום/צ’אט), reconnect, `publish_ride_event` / `keys.py` | **סעיפים 1, 5, 14** + `frontend/src/types/wsEvents.ts` |
| Google Maps (Directions + Distance Matrix + Circuit Breaker + health) | **סעיף 2** (טבלת APIs), **Latest architecture updates**, סעיף **12** (גיאו) |
| CI/CD, GHCR, S3 + CloudFront, מובייל, pytest, Vitest מקומי, k6, phonenumbers | **סעיפים 2, 9, 12** |
| Unread WS, קבוצות, SQLAdmin, UUID, RTL, EIA | **סעיף 13** |
| Defensive programming | **סעיף 7ב** |

---

## 12. דגשים נוספים (סקירה מעמיקה — מה להשוויץ)

נבדק מול הקוד וה-repo; אלה נקודות חזקות שלא תמיד בולטות ב”סיפור הראשי”:

### CI/CD ואיכות קוד

| מה | פירוט |
|----|--------|
| **GitHub Actions — 3 pipelines נפרדים** | `backend`: **Ruff** (`check` + `format --check`), **`DATABASE_URL` ברמת ה-job**, **`alembic upgrade head`** ואז **pytest** על Postgres שירות; `frontend` (**ESLint** + **build**); `chat-ws` (**go build** + **go vet**). טריגר לפי `paths`. |
| **Deploy אוטומטי ל-EC2 (backend/main)** | לאחר הצלחת CI ב-`main`: publish image ב-GHCR (`latest` + `sha`), deploy over SSH, בדיקות health עם retries, ו-rollback אוטומטי לתג קודם. פתרון פרגמטי לסביבת `t3.medium` בלי ALB ובלי שכפול קבוע של סטאקים. |
| **דחיפת images ל-GHCR** | על push ל-`main`: build ו-push ל-`linkup-backend`, `linkup-frontend`, `linkup-chat-ws` — מוכן לפריסה מקונטיינרים. |
| **uv ב-CI** | התקנת תלויות backend דרך `uv sync --frozen`; **`uv.lock`** + **`pyproject.toml`** — כולל נעילת **`phonenumbers==8.13.48`** לאימות מספרים ישראליים עקבי. |
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
| **Geocode cache 24h** | שמירת תוצאות כתובת→קואורדינטות ב-Redis ל-24 שעות (fail-open) כדי להפחית קריאות חיצוניות חוזרות ולשפר latency בחיפושים חוזרים. |
| **Circuit breaker (Google)** | שלושה singletons ב־**`circuit_breaker.py`**; מצב **`closed` / `open` / `half_open`** נחשף ב־**`GET /api/v1/health`** תחת **`circuit_breakers`** — לא משנה את **`status`** הכללי של Health. |

### אבטחה HTTP מעבר ל-JWT

| מה | פירוט |
|----|--------|
| **Revocation ל-access** | **`jti`** ב-access + **`denylist:{jti}`** ב-Redis עד `exp` אחרי logout — לא רק ניקוי refresh ב-DB. |
| **Idempotent POST (נוסע)** | **`Idempotency-Key`** + **`SET NX`** + מטמון **201** ל־`request-ride-from-search` — דפוס Stripe; פירוט **§7ה**. |
| **Security headers** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, **HSTS** כש-HTTPS; **COOP** מכוון כדי **Google OAuth popup** יעבוד. |
| **CORS כפול** | middleware רגיל + **EnsureCORS** גם על תגובות שגיאה (כולל 500) — פחות “CORS נשבר רק על שגיאה”. |

### תשתית וסקייל — מה שכדאי להזכיר בראיון (מעבר לרשימה הראשית)

| מה | למה זה חשוב |
|----|----------------|
| **Redis — שני logical DB (0 ו-1)** | הפרדת cache/rate-limit/denylist/idempotency/pubsub-API מ-pub/sub של צ’אט והשלמות AI — פחות הפרעות והתנגשויות מפתחות. |
| **Outbox LISTEN/NOTIFY** | עדיפות לאירוע אחרי commit לעומת polling גס בלבד — פחות latency ועומס על DB. |
| **Scheduled publisher replica=1** | מניעת כפל פרסום משימות מתוזמנות — דפוס קלאסי ב-job schedulers. |
| **Presigned PUT ל-S3** | ה-API לא מעביר bytes של תמונות — פחות CPU/זיכרון ו-timeoutים בשרת. |
| **Cursor pagination** | חיפוש נסיעות וצ’אט בלי offset עמוק — יציב יותר בנתונים גדלים. |
| **קונטרקט שגיאות אחיד** | `LinkUpError` + `trace_id` — לקוחות ו-Sentry מיושרים; פחות דיבוג “בעלם”. |
| **Sentry + Prometheus/Grafana (פעיל)** | **Sentry:** `sentry_sdk.init()` ב-`setup_logging()` כש-`SENTRY_DSN` מוגדר — FastAPI/SQLAlchemy/Redis integrations, `traces_sample_rate=0.1`; `capture_exception` ל-5xx בלבד (מניעת רעש). פרונט: `Sentry.init()` ב-`main.tsx` + `captureException` ב-axios interceptor (5xx), `ChatErrorBoundary`, `RouteErrorBoundary`. **Prometheus/Grafana:** backend חושף `/metrics`; compose profile `monitoring` מרים `prometheus`+`grafana` עם provisioning + dashboard בסיסי. DSN ב-`.env` בלבד, לא ב-git. **שאילתות:** אין pipeline אוטומטי ל-EXPLAIN ANALYZE; סקירה ידנית מומלצת על נתיבים כבדים עם `pg_stat_statements`. |

### אימות טלפון (ישראל / בינלאומי)

| מה | פירוט |
|----|--------|
| **phonenumbers** | הולידציה ב־`app/core/utils/validators.py` עם ספריית **`phonenumbers`**. הגרסה **נעולה ל־`8.13.48`** ב־`pyproject.toml` / `uv.lock` — יציבות מול מטא־דאטה ישראלית (גרסאות 9.x שינו התנהגות לטווחי מנוי מסוימים). |

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
| **Unread צ’אט** | Backend מפרסם ל-Redis `chat:notification:{recipient_id}`; **chat-ws** מעביר ל-WebSocket של הנמען → עדכון badge / `unread_count` בלי רענון מלא. |
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
| **שכבת API** | כל קריאת HTTP דרך `src/api/<תחום>.ts` — לא ייבוא ישיר של `api` מ־`client` בקומפוננטות (חריגים מתועדים: `AuthContext`, `presence.ts`). **`passengers.ts` / `useJoinRide`** — **`Idempotency-Key`** יציב לפעולה דרך **ref** (ראו **§7ה**). |
| **שגיאות** | `getApiErrorMessage` / `getApiStatus` / `isTimeoutOrAbortError` ב־`utils/apiError.ts` + **Vitest** (`apiError.test.ts`). ב־hooks: fallback אחיד עם **`apiErr('err_*')`** (מפתחות ב־`common.json`) במקום מחרוזות עברית קשיחות. |
| **i18n / טיפוגרפיה** | **`LangContext`** — `lang`, `dir`, **`--font-primary`**; קבצי תרגום תחת `src/i18n/locales/`; ב־**`*.module.css`** — `var(--font-primary)` / `var(--font-numeric)` (חריג: `LangToggle`). |
| **Code splitting** | **`React.lazy` + `Suspense`** לדפים (טעינה עצלה), מסכי טעינה עקביים; **מסלולי `/admin/*`** נטענים עצלנית דרך מודול `features/admin`. |
| **State גלובלי** | **`ChatContext`** + `chatReducer`; **`GroupContext`** — רשימת קבוצות, `activeChipId` משותף ל־**MyRides** / **MyRequests** (פילטר צ’יפים); איפוס צ’יפ אחרי leave/close קבוצה בזרימות ניהול. |
| **פיד התראות (in-app)** | **`useChatNotificationsWebSocket`** (`useReconnectingWebSocket`, **`onOpen`** → רענון פיד + unread + `linkup-notifications-refresh`) + **`useChatNotificationsFeed`** — polling REST **~5 דקות** כגיבוי; משולב ב־`ChatContext`. |
| **בקשות נוסע** | הוק **`useMyRequests`** — לוגיקת MyRequests מרוכזת. |
| **הזמנות שלי (VM)** | **`useMyBookings`** — קומפוזיציה מ־`useMyBookingsPassenger` + `useMyBookingsDriver`; החזרה **מקוננת** (`passenger`, `driver`, `chat`) + יצוא **`MyBookingsViewModel`**. טעינה ב־**קריאת REST אחת לטאב** (`/bookings/driver-summary`, `/bookings/passenger-summary`) במקום N+1. כרטיס נוסע: **`PassengerBookingCard`**. |
| **עיצוב** | **`tokens.css`**, `ThemeContext`, מצב כהה — פחות אינליין CSS בדפי auth. |
| **איכות** | בדיקות יחידה ל־reducer ול־utils קריטיים (`chatReducer`, `apiError`, `myBookings.utils`, MessageThread WS, `ErrorBanner`) לפי [`FRONTEND_REFACTOR_AND_QUALITY.md`](../frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md). |
| **Zod + WebSocket** | סכימות ב־**`src/types/wsEvents.ts`**; אימות בכניסה ב־hooks וב־**`processChatWebSocketMessage`** — ראו **סעיף 5**. |

*בראיון:* “פרדתי שכבת API, פיצלתי דפים כבדים להוקים, ואיחדתי פילטר קבוצות ב-context כדי שלא יישבר בין מסכים.”

---

*עודכן כחלק מתיעוד הפרויקט — כולל מאגר DB ניתן להגדרה, **auth בעומס** (bcrypt ב-executor, pool, rate limit, outbox), **`jti` + Redis denylist ל-access אחרי logout** (ADR §18), **Idempotency-Key לבקשת הצטרפות מחיפוש** (ADR §19, **`passengers.ts`**, **`useJoinRide.ts`** + **`useSearchRides.ts`**), **Circuit Breaker ל-Google Maps בבקאנד + `circuit_breakers` ב-`/api/v1/health`** (ADR §20, `infrastructure/geo/circuit_breaker.py`), **PgBouncer ממומש ב-Compose** (internal-only + migration isolation + asyncpg compatibility), **structlog + `X-Request-ID` / ContextVar** (`ARCHITECTURE.md` — Observability), סעיף **0א** (סיכום trade-offs), חיזוק OTP, מניעת user enumeration בלוגין (OWASP), **GitHub Actions + GHCR** (backend: **Ruff** → **Alembic upgrade head** → **pytest** עם **`DATABASE_URL` אחיד**; chat-ws: **go build** + **go vet**), **pydantic-settings** (`validation_alias` ל־`DATABASE_URL` / `REDIS_URL`), **Vitest + ריפקטור ארגון בפרונט** (`FRONTEND_REFACTOR_AND_QUALITY.md`), **Zod לאימות WebSocket** (`frontend/src/types/wsEvents.ts`), **מסך אדמין דסקטופ** (`ADMIN_DASHBOARD.md`, `/admin` + `/api/v1/admin`), **k6** עם דוגמת תוצאות, **phonenumbers==8.13.48**, **S3 + CloudFront (קריאה ציבורית) ואווטאר ב-prefix גרסתי immutable**, **i18n + לוקאליזציה + `apiErr` + פונטים ב־CSS Modules** (`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` §10–12), ו-**Docker Compose** (שירות **migrate**, healthcheck ל-backend, `.env` בשורש + `backend/.env`, recreate לקונטיינר אחרי שינוי env).*
