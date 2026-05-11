# ארכיטקטורה - chat-ws vs backend

## עקרון יסוד: הפרדת אחריות

### chat-ws (Go) - WebSocket + HTTP מינימלי ל-presence
**תפקיד:** העברת הודעות real-time מ-Redis ל-WebSocket clients; **אחריות מלאה על `online`** (מפתח `presence:*` ב-Redis DB1).

**מה כן:**
- ✅ WebSocket connections management
- ✅ JWT authentication (WS + HTTP presence)
- ✅ Subscribe ל-Redis (**`chat:conversation:*`**, **`chat:typing:*`**, **`user:*:events`**, … + **`user:offline`** + **`user:online`**) — בחיבור: `PUBLISH user:online` → WS `user_online`; בניתוק: `user:offline` → `user_offline` (עדכון מיידי ב-UI). פריימים מ-`user:*:events` נשלחים ללקוח דרך **`SendToUser`**. **אין** `chat:notification:*` — אותו זרם נבלע תחת **`user:*:events`**. לקוחות Redis נפרדים ל-subscribe כדי לא לחסום עם `PSubscribe` של הצ'אט.
- ✅ Forward messages ל-clients
- ✅ Typing events (`typing_start` / `typing_stop`) דרך Redis (`chat:typing:*`)
- ✅ **HTTP `GET /presence/{user_id}`** — `online` מ-Redis; `last_seen` מ-backend (`GET /api/v1/users/{id}/last-seen`) כשצריך
- ✅ Presence / debounce לעדכון last-seen ב-DB:
  - `presence:{user_id}` TTL 60s
  - `debounce:last_seen:{user_id}` + `last_seen:hold:{user_id}`
- ✅ **הגנה על פריימים נכנסים (hub):** **`conn.SetReadLimit(int64(maxMessageSize))`** עם **`maxMessageSize = 2048`** ב־[`internal/hub/conn.go`](internal/hub/conn.go) — מגבלה על גודל מסר WebSocket מהלקוח; חריגה סוגרת את החיבור בצד gorilla עם `ErrReadLimit`. **Rate limit פר־חיבור** (`golang.org/x/time/rate`, **`rate.Limit(30)`/`Burst 60`**) על פרסום **`typing_start`/`typing_stop`** ל־Redis בלבד — פריים שחורגים נזרקים בשקט; **`ping`** לא נספר ולא נחסם.
- ✅ **`/healthz` (H7):** בודק Redis PING + `Hub.SubscribersHealthy()` — שלוש `atomic.Int64` timestamps (chat/offline/online), threshold 2 דקות. Docker Compose healthcheck פוגע בנקודה הזו.
- ✅ **Graceful HTTP shutdown (H8):** `*http.Server` + `srv.Shutdown(10s)` — ב-SIGTERM ניקוי subscribers ואז drain מסודר של חיבורים פעילים.
- ✅ **Pong/read deadline (H9):** `SetReadDeadline(pongWait=60s)` + `SetPongHandler` — לקוחות מתים מזוהים ומנותקים תוך 60 שניות; אין דליפת goroutines.
- ✅ **Panic recovery (H10):** `defer safego.RecoverPanic(...)` ([`internal/safego/safego.go`](internal/safego/safego.go)) על כל goroutine עצמאית — panic לא מפיל את התהליך.

**מה לא:**
- ❌ Calendar export
- ❌ AI analysis logic (רק forward אם צריך)
- ❌ Business logic

### backend (Python) - ה-API Server
**תפקיד:** כל ה-API endpoints והלוגיקה העסקית

**מה כן:**
- ✅ WebSocket ב-FastAPI לנסיעות/בוקינגים (`/api/v1/rides/...`, `/api/v1/bookings/...`) — אימות ב-`get_current_user_ws`: **JWT בלבד** (`WsUser`), בלי DB בזמן connect (פרטים: `ARCHITECTURE.md` בשורש, `docs/architecture/REALTIME.md`). **אין** כרגע `/api/v1/notifications/ws`; התראות in-app משתמשות ב-REST + אירועי `user:{id}:events` דרך chat-ws.
- ✅ REST API endpoints
- ✅ Calendar export (`GET /api/v1/chat/conversations/{id}/calendar.ics`)
- ✅ תוצאות ניתוח AI ב־**`chat_analysis`**; **אין** `GET …/analysis` בראוטר הצ’אט החי — אל תסמכו על נתיב כזה עד שקיים בקוד (סקריפטים ישנים/k6 עשויים להזכיר מתוכנן)
- ✅ Business logic
- ✅ Database operations

## AI Analysis - איפה?

**ניתוח AI רץ ב-backend workers:**

1. **מסלול פעיל (קוד):** **`task-worker`** — משימות scheduled ( למשל `execute_chat_timeout_job`) קוראות **ישירות** ל־`handle_conversation_completion` בתוך ה-backend (DB + Groq + `chat_analysis` + Outbox). אין בהכרח פרסום Redis ל-chat-ws בנתיב הזה.
2. **מסלול מאזין:** **`ai-worker`** — `run_chat_completion_redis_listener` נרשם ל־`chat:completion:*` על **`REDIS_CHAT_URL`**. אם מישהו מפרסם JSON עם `conversation_id` + `trigger_user_id`, אותו handler רץ.

**מתואם ארכיטקטונית / עתידי:** פרסום **`chat:completion:{conversation_id}`** לטריגר מהיר — **לא** מופיע בקבצי ה-Python שסרקנו ב-backend; אל תסמכו עליו כלייציב עד יישום מפורש.

## Calendar Export - איפה?

**חייב להיות ב-backend בלבד** - זה API endpoint שהמשתמש מבקש דרך HTTP.

**API Endpoint:**
- `GET /api/v1/chat/conversations/{id}/calendar.ics`
- קורא הודעות מ-DB
- מנתח (או משתמש בתוצאות ניתוח קיימות)
- מייצא ל-iCal
- מחזיר קובץ `.ics`

**מיקום קוד:**
- ✅ `backend/app/domain/chat/calendar/` - לוגיקת calendar (נדרש)
- ✅ `backend/app/domain/chat/router.py` — endpoints REST (כולל `calendar.ics` — כרגע 501)
- ❌ אין microservice AI נפרד; הניתוח רץ מ־**workers** מתוך image ה-backend (`task-worker` כטריגיר עיקרי; `ai-worker` — מאזין Redis אופציונלי).

**למה לא ב-chat-ws?**
- ייצוא iCal וניתוח שיחה הם לוגיקת API/DB; chat-ws הוא רק real-time fan-out
- תוצאת ניתוח ב־**`chat_analysis`**; הנגישות ב־REST — כפי שנרשם למעלה ב־«backend / מה כן» (לא מכפילים כאן)

## זרימה מומלצת

### חוזה payloads על `chat:conversation:{id}` (מסירה נקודתית)

כל פריים שמגיע ל־Go דרך `PublishChatMessage` (אחרי `PSubscribe` על `chat:conversation:*`) חייב לכלול **`recipient_id`**: מזהה המשתמש שאליו chat-ws מעביר את הפריים (`SendToUser`). זה נכון גם להודעת צ'אט וגם לאירוע `message_read` מה־backend — אחרת `RecipientID` ריק והפריים לא יגיע ללקוח.

### 1. שליחת הודעה
```
Client → POST /api/v1/chat/conversations/{id}/messages (backend)
       → Backend שומר ב-DB
       → Backend מפרסם ל-Redis (chat:conversation:{id})
       → chat-ws מקבל מ-Redis → שולח ל-WebSocket
       → לאחר שליחה: backend מעדכן גם **`users.last_active_at`**
       → טריגר AI: כרגע עיקרית דרך **שעון idle ב-task-worker**, לא בשורת “הודעת סיום” אחת מתוך ה-Redis chat flow
```

### 2. ניתוח AI (רקע)
```
task-worker (scheduled) ──► handle_conversation_completion ──► Groq ──► chat_analysis + Outbox

ai-worker ──► (אופציונלי) מאזין Redis chat:completion:* ──► אותו handler — רק אם קיים publisher
```
(אין כרגע endpoint REST ייעודי ב-spa לקריאת JSON הניתוח — התוצאה קיימת ב-DB.)

### 3. ייצוא ללוח שנה
```
Client → GET /api/v1/chat/conversations/{id}/calendar.ics (backend)
       → Backend קורא הודעות מ-DB
       → Backend מנתח (או משתמש בתוצאות קיימות)
       → Backend מייצא ל-iCal
       → מחזיר קובץ .ics
```

## התראות: צ'אט מול פיד in-app

- **עדכון unread / פיד:** הכל עובר ב־**`user:{id}:events`** — `invalidate` (unread או notifications) או **UserEvent** מ־`publish_user_event`. chat-ws מנתב ל־**`/ws`** בלי ערוץ נפרד `chat:notification:*`.
- **פיד התראות האפליקציה (מסך / באדג'):** הרשימה מ־**`GET /api/v1/users/me/notifications`** + polling ב־`useChatNotificationsFeed`. רענון חי ב־**`ChatContext`** + **`useUserEventStream`**. אין WS נפרד ב-FastAPI ל־`/notifications/ws` — ראו [`ARCHITECTURE.md`](../ARCHITECTURE.md) ו־[`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).

## סיכום

| Feature | Location | Reason |
|---------|----------|--------|
| WebSocket connections | chat-ws (Go) | Real-time, performance |
| REST API endpoints | backend (Python) | Standard API pattern |
| In-app notification **feed** (REST + refresh events) | backend REST + **chat-ws** (`user:{id}:events`) | רשימה ב-REST; דחיפת רענון על אותו WS כמו צ'אט |
| Per-user invalidate + domain events | chat-ws (`user:*:events` → `SendToUser`) | חיבור WS יחיד |
| Calendar export | backend (Python) | API endpoint |
| AI analysis | backend worker (`ai-worker`) | Async, Redis DB 1 listener |
| AI analysis persistence | backend DB (`chat_analysis`) | worker אחרי completion |
| Business logic | backend (Python) | Centralized |
| Auth load testing (k6) | `backend/load_test.js` | עומס על REST register/login — לא ב-chat-ws |
