# Linkup — הדגשים הנדסיים (Portfolio / Senior)

**שם הקובץ:** `docs/ENGINEERING_HIGHLIGHTS.md` (בשורש הפרויקט, תחת `docs/`).

מסמך זה אוסף **במקום אחד** את הפיצ’רים, הטכנולוגיות, הדפוסים וההחלטות שמיועדות ל**סקייל, אמינות ותחזוקה** — כדי להציג את הפרויקט ברמת מומחה.  
*זה סיכום “להצגה”, לא מיפוי כל שורה בקוד; אחרי סקירה מול ה-repo הוכנסו גם workers, AI, FCM, Brevo, Google, **חיזוק auth ועומס מקבילי**, **k6**, **ריפקטור async משמעותי ב-passengers/bookings/rides**, **ריפקטור ארגון בפרונט**, ו**מסך אדמין פנימי (React + `/api/v1/admin`)**.*

לפרטים טכניים עמוקים יותר: `../ARCHITECTURE.md`, `architecture/REALTIME.md`, `architecture/EVENTS.md`, `architecture/DATABASE.md`, `architecture/API.md`, `backend/docs/GOOGLE_OAUTH.md`.

---

## 1. מה בנינו (מוצר + יכולות)

| תחום | יכולות |
|------|--------|
| **נסיעות** | פרסום נסיעות, חיפוש (כולל גיאו / PostGIS), סטטוסים, שיוך לקבוצה / ציבורי |
| **הזמנות** | בקשה, אישור/דחייה, race-safe (locks) |
| **צ’אט** | הודעות real-time, typing, נראות (online / last seen), **unread** (Redis→WS), קריאת שיחה |
| **קבוצות** | יצירה, **קוד הזמנה** (`invite_code`), הצטרפות בקישור, ניהול admin |
| **AI** | סיום שיחה → ניתוח (Groq) → שמירה + התראות |
| **התראות** | מייל (**Brevo**), Push (**FCM** — מהשרת רק מפת `data` ב־FCM, בלי שדה `notification` של Firebase; בחזית **Toast קופץ + צליל**, ברקע התראת מערכת דרך SW), in-app |
| **משתמשים** | JWT + Refresh ב-DB, **כניסה עם Google** (OAuth / `id_token`), אווטאר (S3 + worker); שדה **`is_admin`** לגישה ל־`/api/v1/admin/*` |
| **אדמין / תפעול** | ממשק ווב **`/admin`** (מודול `features/admin`): סטטיסטיקות, בריאות, משתמשים (הפעלה/הרשאת אדמין), נסיעות (ביטול), קבוצות, Outbox (requeue), lookup; **lazy routes**, אישור לפני מוטציות, toasts; בקאנד **`get_current_admin_user`** + לוג `[admin_audit]` — **`ADMIN_DASHBOARD.md`** |
| **מפות** | Google: **Geocoding**, **Directions**, **Distance Matrix**, **Maps JS**; geocoding הוא **Google-only** עם cache ב-Redis (24h) |
| **GPS בזמן אמת** | מיקום נהג לנוסעים, מיקום נוסעים לנהג (ערוצי Redis נפרדים + WS). **פרונט:** POST מותאם ב־throttle (~1.5s), `maximumAge: 0` לשידור, `useMapMarker` — יצירת marker פעם אחת ועדכון מיקום בלבד (בלי ריצוד), מפת Google. **Zod** על פריימי WS בכניסה — `frontend/src/types/wsEvents.ts`. פירוט: `docs/architecture/REALTIME.md`. |

---

## 2. סטאק טכנולוגי

| שכבה | טכנולוגיה |
|------|-----------|
| API | **Python 3**, **FastAPI**, async SQLAlchemy, **Alembic** |
| Real-time chat WS | **Go** — שרת WebSocket ייעודי (`chat-ws`) |
| Frontend | **React**, **Vite**, TypeScript, **Zod** (אימות JSON מ-WebSocket בפרונט) |
| DB | **PostgreSQL 15** + **PostGIS** (גיאומטריה, מרחקים) |
| Cache / Pub-Sub | **Redis** — **הפרדה ל-DB 0 (API) ו-DB 1 (צ’אט + completion)** |
| Broker | **RabbitMQ** — תורים לאירועים ומשימות כבדות |
| אחסון | **S3** (אווטארים) |
| פריסה | **Docker Compose**; **Kubernetes** (למשל `k8s/chat-ws`) |
| AI (צ’אט) | **Groq** — מודל Llama (למשל `llama-3.3-70b-versatile`) לניתוח שיחה |
| מייל | **Brevo** (API transactional) |
| Push | **FCM** — `fcm_token` ב-DB; שליחה דרך Firebase Admin עם **`data` בלבד** (ללא בלוק `notification` של FCM); הצגה בידי האפליקציה: ברקע SW על `push`; בחזית **Toast + צליל** (`onMessage` + `payload.data`) |
| כניסה Google | **Google Sign-In** — אימות `id_token` ב-backend; client ID משותף FE/BE (`backend/docs/GOOGLE_OAUTH.md`) |

### כל סוגי ה-API שקשורים למפות / מיקום (מלא)

**מפתח אחד לרוב Google Maps Platform:** `GOOGLE_MAPS_API_KEY` — מופעל ב-Console עבור כל ה-APIs הרלוונטיים (Geocoding, Directions, Distance Matrix, Maps JavaScript).

| # | API / שירות | איפה בקוד | תפקיד |
|---|-------------|-----------|--------|
| 1 | **Google Maps Geocoding API** (`/maps/api/geocode/json`) | `GeocodingService` — כתובת→קואורדינטות ו-**reverse** (קואורדינטות→כתובת) | זרימות דרך `domain/geo` (למשל מיקום נוכחי, עיבוד כתובות); טיפול ב-429 וכו’. |
| 2 | **Google Directions API** (`/maps/api/directions/json`) | `infrastructure/geo/client.py` | עד **3 מסלולים** חלופיים, `language=he`, polyline לתצוגה. |
| 3 | **Google Distance Matrix API** (`/maps/api/distancematrix/json`) | אותו `GeoClient` | זמן נסיעה ומרחק מוצא–יעד (מיושר למסלולים). |
| 4 | **Google Maps JavaScript API** (`maps/api/js?key=…`) | פרונט: `loadGoogleMaps`, מודלי מפה חיים / מסלול | מפת **Google** באפליקציה; המפתח מגיע מ-**`GET /api/v1/geo/maps-key`** (או `VITE_GOOGLE_MAPS_API_KEY`). |
| 5 | **Geocode cache (Redis, 24h)** | `geocode_cache` (Redis) + `GeocodingService` (Google) | כתובת→קואורדינטות עם cache fail-open (חוסך קריאות חיצוניות חוזרות) |
| 6 | **OSRM** (דוגמה ציבורית) | קבוע `OSRM_URL` ב-`GeoClient` | **לא** בשימוש בזרימת `fetch_raw_routes` הנוכחית (שם רק Google); נשאר כתשתית אפשרית. |

**כניסה עם Google (לא מפות):** **OAuth / Identity** — `GOOGLE_CLIENT_ID`, ראה `backend/docs/GOOGLE_OAUTH.md`.

**לסיכום לראיון:** “במפות יש לי **ארבעה APIs של Google Platform** — Geocoding (כולל reverse), Directions, Distance Matrix, ו-JavaScript למפה בדפדפן; geocoding הוא **Google-only** עם cache ב-Redis; מפתח Maps נפרד מ-OAuth של Login.”

---

## 2א. Workers: מה רץ כל הזמן ומה לפי זמן

תהליך **`outbox-worker`** (`python -m app.workers.main_worker`) מריץ **במקביל** כמה לולאות:

### רצים כל הזמן (כל עוד ה-worker חי)

| רכיב | תפקיד |
|------|--------|
| **3 consumers ל-RabbitMQ** | `notifications_queue` (מייל+FCM), `avatar_upload_queue`, `scheduled_tasks_queue` — **מאזינים** לתור ומטפלים בהודעות כשהן מגיעות. |
| **Outbox poller** | סורק `outbox_events` (PENDING) ומפרסם ל-RabbitMQ — רצוף/תדיר. |
| **Redis listener — סיום צ’אט** | מאזין ל-`chat:completion:*` (DB 1), מפעיל ניתוח **AI (Groq)** ושמירה ל-DB. |
| **Scheduled publisher (לולאה)** | כל ~**60 שניות** בודק אם “הגיע הזמן” לפרסם משימה מתוזמנת ל-exchange `scheduled` (הלוגיקה הכבידה רצה ב-consumer, לא כאן). |

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

- **Backend stateless** — כל הלוגיקה העסקית ב-FastAPI; אפשר להרחיב replicas; WebSocket לצ’אט **לא** על אותו process (מפורק ל-Go).
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

- **עדכוני נסיעה**: WS ב-FastAPI + Redis Pub/Sub; **מקור אמת לשמות ערוצים** — `app/infrastructure/redis/keys.py` (`get_ride_channel` וכו'). **נקודת כניסה אחת לשידור** — `publish_ride_event` ב-`app/domain/rides/broadcast.py` (אירועים כמו `RIDE_STARTED` / `RIDE_ENDED` / `RIDE_CANCELLED`). חיבור ל-`/rides/ws/{ride_id}` דורש `?token=JWT` (כמו שאר ה-WS ב-backend).
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
- **יתרון לסקייל**: אפשר להוסיף workers שמושכים מהתור בלי להעמיס על ה-API; **backpressure** — אם שליחת מייל איטית, התור גודל והמערכת לא קורסת.

### 6.3 Outbox — החיבור בין סינכרון לאסינכרון

- באותה **טרנזקציה** עם עדכון עסקי נכתב שורה ל-`outbox_events`.
- אחרי commit, תהליך נפרד מפרסם ל-RabbitMQ. כך **לא** יוצא מצב: “הזמנה נשמרה אבל האירוע לתור אבד”.
- פירוט exchanges/queues: `architecture/EVENTS.md`.

---

## 7. דפוסים ו”טריקים” ברמת קוד

| דפוס | למה |
|------|-----|
| **DDD** | דומיינים מבודדים (rides, bookings, chat, …) — קל להרחבה וטסטים. |
| **Pessimistic locking** | אישור/ביטול הזמנה תחת `SELECT FOR UPDATE` — מונע race ו”כפל” לוגיקה תחרותית על אותה נסיעה. |
| **Async SQLAlchemy 2.0 migration** | זרימות ליבה בדומיינים passengers/bookings/rides עברו ל-`AsyncSession` + `select/execute`; פעולות sync נשמרו רק למקטעים שדורשים locking/transactional guarantees. |
| **JWT קצר + Refresh ב-DB** | אבטחה + אפשרות לביטול sessions. |
| **Rate limiting (Redis)** | על **register**, **login / refresh** ונקודות auth נוספות — מונה ב-Redis, חלון זמן + מקסימום בקשות ל-IP — מגביל הרשמה/כניסה אגרסיבית. |
| **מניעת username enumeration (OWASP)** | לוגין: **אותה** `InvalidCredentialsError` (401) לאימייל שלא קיים ולסיסמה שגויה — לא חושפים אם המשתמש רשום. |
| **bcrypt ב-thread pool** | `get_password_hash` / `verify_password` — **async** עם `asyncio.get_running_loop().run_in_executor` — לא חוסמים את לולאת ה-ASGI תחת עומס סיסמאות. |
| **Request ID** | `X-Request-ID` — מעקב בין לוגים לבקשה. |
| **JSON logging בפרודקשן** | ingestion ל-ELK / CloudWatch בעתיד. |
| **Uvicorn + מספר workers** (`UVICORN_WORKERS` ב־Docker Compose; `backend/.env.example` מציין 4) | ניצול מספר cores ל-API. |
| **Redis DB נפרד לצ’אט** | בידוד עומס pub/sub ומפתחות צ’אט מ-cache הכללי של ה-API. |

### 7ב. Defensive Programming (תכנות הגנתי) — כן, ממומש בפרויקט

**Defensive programming** = להניח שתקלות, קלט שגי ותחרות קיימים; להגן על המערכת במקום “לקרוס בשקט”. ב-Linkup זה בא לידי ביטוי בין היתר ב:

| שכבה | דוגמאות מהקוד |
|------|----------------|
| **עסקי / DB** | בדיקות `if not ride` / בעלות לפני פעולה; **pessimistic lock** על הזמנות; **Outbox** כדי שלא יאבדו אירועים אחרי commit. |
| **רשת / חיצוני** | **Timeouts** ל-Google Geocoding / Directions; טיפול ב-**429** (rate limit) עם הודעה למשתמש; debounce **last-seen** + ביטול ב-reconnect — לא מציפים DB ולא מעדכנים “offline” בטעות. |
| **תשתית** | **`pool_pre_ping`**, **`pool_timeout`**, **`pool_recycle`** — מאגר DB עמיד יותר; **rate limit** על register + login/refresh; **FCM** — טוקן לא תקף מטופל (איפוס / דילוג). |
| **chat-ws (Go)** | `if redisClient == nil` לפני פעולות; **select default** על ערוץ Send; לקוחות Redis נפרדים ל-`user:offline` ול-`user:online` שלא ייתקעו עם `PSubscribe` של הצ’אט. |
| **API / HTTP** | **LinkupError** + handlers מרוכזים; **CORS** גם על תגובות שגיאה; אימות JWT לפני WS ולפני `/presence`. |
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
| סשן | JWT (HS256), `SECRET_KEY` חובה בפרודקשן; אותו סוד ל-chat-ws לאימות WS. |
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

## 8. AI וצ’אט “חכם”

- סיום שיחה → publish ל-`chat:completion:*` על Redis DB 1.
- **outbox-worker** (`run_chat_completion_redis_listener`) מאזין, קורא ל-**Groq** (Llama), שומר תוצאות; אפשר המשך דרך outbox (התראות וכו’).
- ייצוא **iCal** ו-API לניתוח — ב-backend בלבד (לא ב-Go).

### FCM + מייל (איפה בקוד)

- **FCM (Backend)**: `app/domain/notifications/channels/push/client.py` — `messaging.Message` עם **`data` בלבד** (ללא `notification`), כולל `title` ו־`body` כמחרוזות + שדות metadata נוספים; `push_provider` שולח רק אם יש `fcm_token`; טיפול בטוקן לא תקף.
- **FCM (Frontend)**: `frontend/src/services/fcm.ts` — הרשאות, רישום SW, `getToken` + `PATCH /users/fcm-token`; בחזית `onMessage` → קריאת `title`/`body` מ־**`payload.data`** (גיבוי ל־`notification`) → **Toast קופץ** + צליל; `firebase-messaging-sw.js` — **`push`** → `showNotification` כשהטאב ברקע. פירוט מלא: **`docs/FCM_SYSTEM_SUMMARY.md`**.
- **מייל**: **Brevo** דרך `EmailClient` / `email_provider` — אימות מייל, איפוס סיסמה, התראות עסקיות דרך ה-notification pipeline.

---

## 9. DevOps ופריסה

- **Docker Compose**: healthchecks (כולל **backend** על `/api/v1/health`), סיסמת Redis, volumes ל-RabbitMQ ו-Postgres; שירות **`migrate`** (`alembic upgrade head`, `restart: no`) לפני **backend** ו־**outbox-worker**; שירותי פיתוח (`db`, `redis`, `rabbitmq`, `migrate`, `outbox-worker`, `backend` עם **8000 ל-host**, `chat-ws`) ב־`docker compose up -d`; **frontend** סטטי + **nginx** באותו `docker-compose.yml` עם `profiles: ["prod"]` — סטאק מלא על פורט 80 עם `docker compose --profile prod up -d --build`, **nginx** אחרי **backend** ב־`service_healthy`. קובץ שירות Firebase נטען מ־host ל־**backend** ול־**outbox-worker** (volume read-only; `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env`) — נדרש ל־FCM מה־worker. **פריסה בלי Compose** (למשל image בלבד / K8s): להריץ מיגרציה כ־Job או שלב init נפרד — לא מוטמע ב־`CMD` של image ה-production.
- **`.env` כפול לפי תפקיד:** `.env` **בשורש** (מ־`.env.example`) — רק credentials ש־Compose צורך להקמת Postgres / Redis / RabbitMQ; **`backend/.env`** — כל הגדרות הבקאנד. חייב **יישור** (סיסמאות DB/Redis/RabbitMQ) בין הקבצים. אחרי **שינוי `backend/.env`** — לרענן משתנים בקונטיינר: `docker compose up -d --force-recreate backend` (**לא** מספיק `restart` בלבד — ה-env נצרך בעת יצירת הקונטיינר).
- **גרסאות תמונות קבועות** (לא `latest` בשירותים קריטיים) — builds חוזרים.
- **K8s**: deployment ל-`chat-ws` עם env (למשל `BACKEND_URL`) ל-worker של last-seen.

---

## 10. איך להשתמש במסמך הזה בפורטפוליו

- בקורות חיים / לינקדאין: “Real-time chat (מקליד / מחובר / disconnect עם debounce), Go + Redis, Outbox+RabbitMQ, סינכרון מול אסינכרון, PostGIS”.
- בראיון: **סעיף 4** + **5** (real-time נסיעות + Zod) + **6** + **7ג** (auth בעומס) + **7ב** (defensive) + **12** + **13** + **14** (פרונט).

---

## 11. צ’ק-ליסט — מה מכוסה במסמך

| נושא | מכוסה |
|------|--------|
| מקליד / מחובר / disconnect | סעיף 4 |
| סינכרון / אסינכרון + RabbitMQ | סעיף 6 |
| Workers רצים תמיד vs מתוזמנים | סעיף 2א |
| AI (Groq / Llama) | סעיפים 2, 8 |
| FCM | סעיפים 1, 2, 8 + **`docs/FCM_SYSTEM_SUMMARY.md`** |
| מייל Brevo | סעיפים 1, 2, 6, 8 |
| כניסה עם Google | סעיפים 1, 2, 7א |
| אבטחה + rate limit + OTP + מאגר DB + enumeration + auth בעומס | סעיפים 3, 7, 7א, **7ג**, 7ב, 12 |
| ריפקטור פרונט (API, context, lazy, בדיקות) | **סעיף 14** + `frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md` |
| Zod, WebSocket (נסיעות/מיקום/צ’אט), reconnect, `publish_ride_event` / `keys.py` | **סעיפים 1, 5, 14** + `frontend/src/types/wsEvents.ts` |
| Google Maps (Directions + Distance Matrix) | **סעיף 2** (טבלת APIs) + סעיף 12 |
| CI/CD, GHCR, S3, מובייל, pytest, Vitest מקומי, k6, phonenumbers | **סעיפים 9, 12** |
| Unread WS, קבוצות, SQLAdmin, UUID, RTL, EIA | **סעיף 13** |
| Defensive programming | **סעיף 7ב** |

---

## 12. דגשים נוספים (סקירה מעמיקה — מה להשוויץ)

נבדק מול הקוד וה-repo; אלה נקודות חזקות שלא תמיד בולטות ב”סיפור הראשי”:

### CI/CD ואיכות קוד

| מה | פירוט |
|----|--------|
| **GitHub Actions — 3 pipelines נפרדים** | `backend` (**Ruff** lint + format check + **pytest** על Postgres שירות ב-CI), `frontend` (**ESLint** + **build** = `tsc -b` + Vite), `chat-ws` (**go test** + **go vet** + build). טריגר לפי `paths` — לא מריצים הכל על כל commit. |
| **דחיפת images ל-GHCR** | על push ל-`main`: build ו-push ל-`linkup-backend`, `linkup-frontend`, `linkup-chat-ws` — מוכן לפריסה מקונטיינרים. |
| **uv ב-CI** | התקנת תלויות backend מהירה (`uv pip install`); **`uv.lock`** + **`pyproject.toml`** — כולל נעילת **`phonenumbers==8.13.48`** לאימות מספרים ישראליים עקבי. |
| **בדיקות אבטחה JWT** | `backend/tests/test_security.py` — טוקן תקין, פג תוקף, חתימה שגויה (מקרים קריטיים ל-auth). |
| **בדיקות auth + OWASP enumeration** | `backend/tests/test_auth.py` (דורש `TEST_DATABASE_URL`) — רישום, אימייל כפול, סיסמה שגויה ואימייל לא קיים → אותה שגיאת לוגין. |
| **בדיקות יחידה בפרונט (מקומי)** | Vitest — לדוגמה `frontend/src/utils/apiError.test.ts`, **`frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts`** (אירועי WS / Zod) (`npm run test`); לא חובה ב-CI כרגע (ה-workflow מריץ lint + build). |

### העלאות קבצים — לא דרך ה-API

| מה | פירוט |
|----|--------|
| **Presigned URLs (S3)** | הלקוח מעלה **ישירות ל-S3** (אווטאר + תמונת קבוצה) — ה-API לא עובר בו זרימת bytes; פחות עומס ו-timeoutים. |
| **Pipeline אווטאר** | staging ב-S3 → אירוע ל-RabbitMQ → worker (resize/WebP) → מיקום סופי תחת `avatars/{user_id}/`. |
| **תיעוד CORS ל-bucket** | `docs/S3_CORS.md` — תצורה מודעת לדפדפן. |

### גיאו — שילוב מקורות

| מה | פירוט |
|----|--------|
| **Geocoding** | **Google Geocoding API** (`GeocodingService`) — כתובת→קואורדינטות ו-reverse; עטוף ב-Redis geocode cache (24h, fail-open). |
| **מסלולים** | **Google Directions** + **Distance Matrix**; **Maps JS** בפרונט. |
| **PostGIS** | שאילתות מרחביות וחיפוש נסיעות לפי מיקום. |
| **Geocode cache 24h** | שמירת תוצאות כתובת→קואורדינטות ב-Redis ל-24 שעות (fail-open) כדי להפחית קריאות חיצוניות חוזרות ולשפר latency בחיפושים חוזרים. |

### אבטחה HTTP מעבר ל-JWT

| מה | פירוט |
|----|--------|
| **Security headers** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, **HSTS** כש-HTTPS; **COOP** מכוון כדי **Google OAuth popup** יעבוד. |
| **CORS כפול** | middleware רגיל + **EnsureCORS** גם על תגובות שגיאה (כולל 500) — פחות “CORS נשבר רק על שגיאה”. |

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
| **LinkupError + handlers** | מרכוז טיפול בשגיאות + `X-Request-ID` בתגובה — עקביות לקוח ולוגים. |

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
| **RTL / עברית** | פרונט ווב מותאם **ימין-לשמאל**; Google Directions עם `language=he`. |
| **אגרגציה ב-WS (Go)** | Write pump מאחד כמה הודעות ל-**frame אחד** מופרד ב-`\n` — פחות overhead; הפרונט מפרק שורות ב-`onmessage`. |
| **Graceful shutdown ב-worker** | SIGINT/SIGTERM → ביטול tasks, סגירת RabbitMQ — לא “kill קשה” בלבד. |
| **EIA / דלק (מתוזמן)** | תשתית לסריקת מחירי דלק (מפתח `EIA_API_KEY`) — slot בתור המתוזמן. |

---

## 14. פרונט — ריפקטור וארגון (Vite / React)

מקור אמת מפורט לטבלאות סטטוס: **`frontend/docs/FRONTEND_REFACTOR_AND_QUALITY.md`**. סקירת מבנה קבצים: **`frontend/docs/ARCHITECTURE.md`**.

| ציר | פירוט |
|-----|--------|
| **שכבת API** | כל קריאת HTTP דרך `src/api/<תחום>.ts` — לא ייבוא ישיר של `api` מ־`client` בקומפוננטות (חריגים מתועדים: `AuthContext`, `presence.ts`). |
| **שגיאות** | `getApiErrorMessage` / `getApiStatus` / `isTimeoutOrAbortError` ב־`utils/apiError.ts` + **Vitest** (`apiError.test.ts`). |
| **Code splitting** | **`React.lazy` + `Suspense`** לדפים (טעינה עצלה), מסכי טעינה עקביים; **מסלולי `/admin/*`** נטענים עצלנית דרך מודול `features/admin`. |
| **State גלובלי** | **`ChatContext`** + `chatReducer`; **`GroupContext`** — רשימת קבוצות, `activeChipId` משותף ל־**MyRides** / **MyRequests** (פילטר צ’יפים); איפוס צ’יפ אחרי leave/close קבוצה בזרימות ניהול. |
| **התראות צ’אט** | **`useChatNotificationsFeed`** — טעינת פיד התראות מסונכרנת עם מצב הצ’אט (פחות רענונים מיותרים). |
| **בקשות נוסע** | הוק **`useMyRequests`** — לוגיקת MyRequests מרוכזת. |
| **עיצוב** | **`tokens.css`**, `ThemeContext`, מצב כהה — פחות אינליין CSS בדפי auth. |
| **איכות** | בדיקות יחידה ל־reducer / נוטיפיקציות (`chatReducer`, `notifications.utils`) לפי המסמך. |
| **Zod + WebSocket** | סכימות ב־**`src/types/wsEvents.ts`**; אימות בכניסה ב־hooks וב־**`processChatWebSocketMessage`** — ראו **סעיף 5**. |

*בראיון:* “פרדתי שכבת API, פיצלתי דפים כבדים להוקים, ואיחדתי פילטר קבוצות ב-context כדי שלא יישבר בין מסכים.”

---

*עודכן כחלק מתיעוד הפרויקט — כולל מאגר DB ניתן להגדרה, **auth בעומס** (bcrypt ב-executor, pool, rate limit, outbox), חיזוק OTP, מניעת user enumeration בלוגין (OWASP), **pytest + GitHub Actions + GHCR**, **Vitest + ריפקטור ארגון בפרונט** (`FRONTEND_REFACTOR_AND_QUALITY.md`), **Zod לאימות WebSocket** (`frontend/src/types/wsEvents.ts`), **מסך אדמין** (`ADMIN_DASHBOARD.md`, `/admin` + `/api/v1/admin`), **k6** עם דוגמת תוצאות, **phonenumbers==8.13.48**, ו-**Docker Compose** (שירות **migrate**, healthcheck ל-backend, `.env` בשורש + `backend/.env`, recreate לקונטיינר אחרי שינוי env).*
