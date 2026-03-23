# Linkup — הדגשים הנדסיים (Portfolio / Senior)

**שם הקובץ:** `docs/ENGINEERING_HIGHLIGHTS.md` (בשורש הפרויקט, תחת `docs/`).

מסמך זה אוסף **במקום אחד** את הפיצ’רים, הטכנולוגיות, הדפוסים וההחלטות שמיועדות ל**סקייל, אמינות ותחזוקה** — כדי להציג את הפרויקט ברמת מומחה.  
*זה סיכום “להצגה”, לא מיפוי כל שורה בקוד; אחרי סקירה מול ה-repo הוכנסו גם workers, AI, FCM, Brevo, Google ואבטחה.*

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
| **משתמשים** | JWT + Refresh ב-DB, **כניסה עם Google** (OAuth / `id_token`), אווטאר (S3 + worker) |
| **מפות** | Google: **Geocoding**, **Directions**, **Distance Matrix**, **Maps JS**; בנוסף **Nominatim** בחלק מהזרימות (ראו סעיף 2) |
| **GPS בזמן אמת** | מיקום נהג לנוסעים, מיקום נוסעים לנהג (ערוצי Redis נפרדים + WS) |

---

## 2. סטאק טכנולוגי

| שכבה | טכנולוגיה |
|------|-----------|
| API | **Python 3**, **FastAPI**, async SQLAlchemy, **Alembic** |
| Real-time chat WS | **Go** — שרת WebSocket ייעודי (`chat-ws`) |
| Frontend | **React**, **Vite**, TypeScript |
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
| 5 | **Nominatim (OpenStreetMap)** | `GeoClient` + `geo/utils` (geopy) | גיאוקוד **במסלול אחר** (למשל `RoutingService` / חיפושים שמשתמשים ב-`geo_client`) — **בלי** חיוב Google לשלב הזה. |
| 6 | **OSRM** (דוגמה ציבורית) | קבוע `OSRM_URL` ב-`GeoClient` | **לא** בשימוש בזרימת `fetch_raw_routes` הנוכחית (שם רק Google); נשאר כתשתית אפשרית. |

**כניסה עם Google (לא מפות):** **OAuth / Identity** — `GOOGLE_CLIENT_ID`, ראה `backend/docs/GOOGLE_OAUTH.md`.

**לסיכום לראיון:** “במפות יש לי **ארבעה APIs של Google Platform** — Geocoding (כולל reverse), Directions, Distance Matrix, ו-JavaScript למפה בדפדפן; **בנוסף Nominatim** בחלק מהזרימות; מפתח Maps נפרד מ-OAuth של Login.”

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
| **Disconnect** | **מחיקת** `presence` + **`PUBLISH user:offline`** → WS `user_offline` לכל הלקוחות (שותף רואה “לא מחובר” מיד); **debounce** ל-last-seen ב-DB. **Redis:** שרת אחד, **DB0** backend / **DB1** צ’אט+presence. |
| **Last seen (debounce)** | מפתחות Redis: `debounce:last_seen:{user}` (קצר), `last_seen:hold:{user}` (מחזיק JWT עד אחרי ה-debounce). Worker ב-Go בודק כל כמה שניות: אם debounce פג אבל hold קיים → **PATCH** ל-API `users/me/last-seen` → עדכון `users.last_login`. **חיבור מחדש** מבטל את ה-debounce (מוחק מפתחות) כדי שלא יעדכן “offline” בטעות. |
| **אימות** | אותו **JWT** כמו ה-API (`SECRET_KEY` משותף). |

פירוט ערוצים ומפתחות: `architecture/REALTIME.md`. **Online**: הפרונט קורא `GET` ל-**chat-ws** `/presence/{id}` (אותו Redis DB1 כמו ה-WS).

### מקליד · מחובר · התנתקות — איך זה עובד (להצגה בראיון)

| מה רואים במוצר | מה קורה בטכנולוגיה |
|----------------|---------------------|
| **משתמש מקליד** | הפרונט שולח ב-WebSocket `typing_start` (בדרך כלל עם throttle). כשמפסיקים — `typing_stop` (למשל אחרי שליחה או blur). **chat-ws** מפרסם ל-Redis `chat:typing:*` והמנוי מעביר לאותו conversation לצד השני — **בלי** לגעת ב-DB. זה **אפhemeral** ומתאים למאות אלפי אירועים קצרים. |
| **משתמש מחובר** | בפתיחת WS: Go שם `presence:{user_id}` ב-Redis. **Polling כל ~30 שניות** ל-**chat-ws** `GET /presence/{partner_id}` (Bearer) — `online` מ-Redis DB1; **user_offline** ב-WS מעדכן מיד בלי לחכות לפולינג. |
| **התנתקות (Disconnect)** | Go **מפרסם** `user:offline` ב-Redis; המנוי ב-chat-ws משדר **`user_offline`** ב-WebSocket — **בלי לחכות לפולינג**. במקביל debounce ל-PATCH last-seen. פולינג ל-`/presence/{id}` נשאר גיבוי. |

---

## 5. Real-time נוסף (לא צ’אט)

- **עדכוני נסיעה**: WS ב-FastAPI + Redis broadcast (`ride_{id}`).
- **מיקום נהג / נוסעים**: ערוצים נפרדים (`booking_*`, `ride_*:passenger_locations`) + WS ייעודיים — הפרדת עומס ולוגיקה.

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
| **JWT קצר + Refresh ב-DB** | אבטחה + אפשרות לביטול sessions. |
| **Rate limiting (Redis)** | על **register**, **login / refresh** ונקודות auth נוספות — מונה ב-Redis, חלון זמן + מקסימום בקשות ל-IP — מגביל הרשמה/כניסה אגרסיבית. |
| **מניעת username enumeration (OWASP)** | לוגין: **אותה** `InvalidCredentialsError` (401) לאימייל שלא קיים ולסיסמה שגויה — לא חושפים אם המשתמש רשום. |
| **bcrypt ב-thread pool** | `get_password_hash` / `verify_password` — **async** עם `asyncio.get_running_loop().run_in_executor` — לא חוסמים את לולאת ה-ASGI תחת עומס סיסמאות. |
| **Request ID** | `X-Request-ID` — מעקב בין לוגים לבקשה. |
| **JSON logging בפרודקשן** | ingestion ל-ELK / CloudWatch בעתיד. |
| **Gunicorn + מספר workers** | ניצול מספר cores ל-API. |
| **Redis DB נפרד לצ’אט** | בידוד עומס pub/sub ומפתחות צ’אט מ-cache הכללי של ה-API. |

### 7ב. Defensive Programming (תכנות הגנתי) — כן, ממומש בפרויקט

**Defensive programming** = להניח שתקלות, קלט שגי ותחרות קיימים; להגן על המערכת במקום “לקרוס בשקט”. ב-Linkup זה בא לידי ביטוי בין היתר ב:

| שכבה | דוגמאות מהקוד |
|------|----------------|
| **עסקי / DB** | בדיקות `if not ride` / בעלות לפני פעולה; **pessimistic lock** על הזמנות; **Outbox** כדי שלא יאבדו אירועים אחרי commit. |
| **רשת / חיצוני** | **Timeouts** ל-Google Geocoding / Directions; טיפול ב-**429** (rate limit) עם הודעה למשתמש; debounce **last-seen** + ביטול ב-reconnect — לא מציפים DB ולא מעדכנים “offline” בטעות. |
| **תשתית** | **`pool_pre_ping`**, **`pool_timeout`**, **`pool_recycle`** — מאגר DB עמיד יותר; **rate limit** על register + login/refresh; **FCM** — טוקן לא תקף מטופל (איפוס / דילוג). |
| **chat-ws (Go)** | `if redisClient == nil` לפני פעולות; **select default** על ערוץ Send — לא חוסם לנצח אם buffer מלא; לקוח Redis נפרד ל-`user:offline` שלא ייתקע עם PSubscribe. |
| **API / HTTP** | **LinkupError** + handlers מרוכזים; **CORS** גם על תגובות שגיאה; אימות JWT לפני WS ולפני `/presence`. |
| **פרונט** | `try/catch` על טעינת presence / WS; **פיצול הודעות WS לפי `\n`**; `user_offline` עם **ref** ל-partner כדי לא לאבד עדכון אחרי טעינה אסינכרונית. |
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

- **Docker Compose**: healthchecks, סיסמת Redis, volumes ל-RabbitMQ ו-Postgres; שירותי פיתוח (`db`, `redis`, `rabbitmq`, `outbox-worker`, `backend` עם **8000 ל-host**, `chat-ws`) ב־`docker compose up -d`; **frontend** סטטי + **nginx** ב־override עם `profiles: ["prod"]` — סטאק מלא על פורט 80 רק עם `--profile prod` וקובץ override. קובץ שירות Firebase נטען מ־host ל־**backend** ול־**outbox-worker** (volume read-only; `FIREBASE_SERVICE_ACCOUNT_PATH` ב־`backend/.env`) — נדרש ל־FCM מה־worker.
- **גרסאות תמונות קבועות** (לא `latest` בשירותים קריטיים) — builds חוזרים.
- **K8s**: deployment ל-`chat-ws` עם env (למשל `BACKEND_URL`) ל-worker של last-seen.

---

## 10. איך להשתמש במסמך הזה בפורטפוליו

- בקורות חיים / לינקדאין: “Real-time chat (מקליד / מחובר / disconnect עם debounce), Go + Redis, Outbox+RabbitMQ, סינכרון מול אסינכרון, PostGIS”.
- בראיון: **סעיף 4** + **6** + **7ב** (defensive) + **12** + **13**.

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
| אבטחה + rate limit + OTP + מאגר DB + enumeration | סעיפים 3, 7, 7א, 7ב, 12 |
| Google Maps (Directions + Distance Matrix) | **סעיף 2** (טבלת APIs) + סעיף 12 |
| CI/CD, S3, מובייל, בדיקות | **סעיף 12** |
| Unread WS, קבוצות, SQLAdmin, UUID, RTL, EIA | **סעיף 13** |
| Defensive programming | **סעיף 7ב** |

---

## 12. דגשים נוספים (סקירה מעמיקה — מה להשוויץ)

נבדק מול הקוד וה-repo; אלה נקודות חזקות שלא תמיד בולטות ב”סיפור הראשי”:

### CI/CD ואיכות קוד

| מה | פירוט |
|----|--------|
| **GitHub Actions — 3 pipelines נפרדים** | `backend` (Ruff lint + format check + **pytest**), `frontend` (ESLint + **build**), `chat-ws` (**go build** + **go vet**). טריגר לפי `paths` — לא מריצים הכל על כל commit. |
| **דחיפת images ל-GHCR** | על push ל-`main`: build ו-push ל-`linkup-backend`, `linkup-frontend`, `linkup-chat-ws` — מוכן לפריסה מקונטיינרים. |
| **uv ב-CI** | התקנת תלויות backend מהירה (`uv pip install`). |
| **בדיקות אבטחה JWT** | `backend/tests/test_security.py` — טוקן תקין, פג תוקף, חתימה שגויה (מקרים קריטיים ל-auth). |
| **בדיקות auth + OWASP enumeration** | `backend/tests/test_auth.py` (דורש `TEST_DATABASE_URL`) — רישום, אימייל כפול, סיסמה שגויה ואימייל לא קיים → אותה שגיאת לוגין. |

### העלאות קבצים — לא דרך ה-API

| מה | פירוט |
|----|--------|
| **Presigned URLs (S3)** | הלקוח מעלה **ישירות ל-S3** (אווטאר + תמונת קבוצה) — ה-API לא עובר בו זרימת bytes; פחות עומס ו-timeoutים. |
| **Pipeline אווטאר** | staging ב-S3 → אירוע ל-RabbitMQ → worker (resize/WebP) → מיקום סופי תחת `avatars/{user_id}/`. |
| **תיעוד CORS ל-bucket** | `docs/S3_CORS.md` — תצורה מודעת לדפדפן. |

### גיאו — שילוב מקורות

| מה | פירוט |
|----|--------|
| **Geocoding** | **Google Geocoding API** (`GeocodingService`) + **Nominatim** ב-`GeoClient` לפי זרימה. |
| **מסלולים** | **Google Directions** + **Distance Matrix**; **Maps JS** בפרונט. |
| **PostGIS** | שאילתות מרחביות וחיפוש נסיעות לפי מיקום. |

### אבטחה HTTP מעבר ל-JWT

| מה | פירוט |
|----|--------|
| **Security headers** | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, **HSTS** כש-HTTPS; **COOP** מכוון כדי **Google OAuth popup** יעבוד. |
| **CORS כפול** | middleware רגיל + **EnsureCORS** גם על תגובות שגיאה (כולל 500) — פחות “CORS נשבר רק על שגיאה”. |

### מוצר ופלטפורמות

| מה | פירוט |
|----|--------|
| **Web + Mobile** | **React (Vite)** וגם אפליקציה ב-**Expo/React Native** (`mobile/`) — אותו REST API, לקוחות מרובים. |
| **אימות מייל** | קוד ב-**Redis** (TTL) + מייל דרך Brevo; resend verification; OTP מוגן (**`secrets`**, **`compare_digest`**, מונה ניסיונות). |
| **עומס auth (k6)** | סקריפט אופציונלי **`backend/load_test.js`** — register + login, thresholds ל-p95 ושגיאות; ראו `backend/README.md`. |

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
| **פולינג presence** | **30s** ל-`GET /presence/{id}` ב-chat-ws כ**גיבוי**; `user_offline` ב-WS = עדכון **מיידי**. |
| **קבוצות + הזמנה** | `invite_code` ייחודי, תפוגה אופציונלית, endpoint הצטרפות; העברת admin בקבוצה. |
| **SQLAdmin** | ממשק **ניהול פנימי** (FastAPI-SQLAdmin): משתמשים, נסיעות, הזמנות, בקשות — תפעול ודיבוג. |
| **UUID כמפתחות** | `user_id`, `booking_id`, `ride_id` וכו’ — מניעת התנגשויות ומוכנות לפיצ’ול אופקי. |
| **RTL / עברית** | פרונט ווב מותאם **ימין-לשמאל**; Google Directions עם `language=he`. |
| **אגרגציה ב-WS (Go)** | Write pump מאחד כמה הודעות ל-**frame אחד** מופרד ב-`\n` — פחות overhead; הפרונט מפרק שורות ב-`onmessage`. |
| **Graceful shutdown ב-worker** | SIGINT/SIGTERM → ביטול tasks, סגירת RabbitMQ — לא “kill קשה” בלבד. |
| **EIA / דלק (מתוזמן)** | תשתית לסריקת מחירי דלק (מפתח `EIA_API_KEY`) — slot בתור המתוזמן. |

---

*עודכן כחלק מתיעוד הפרויקט — כולל מאגר DB ניתן להגדרה, bcrypt אסינכרוני, rate limit על register, חיזוק OTP, מניעת user enumeration בלוגין (OWASP), ו-k6 (`backend/load_test.js`).*
