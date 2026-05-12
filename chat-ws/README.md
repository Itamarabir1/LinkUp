# chat-ws – WebSocket server for real-time chat

שרת WebSocket נפרד (Go) לצ'אט real-time. עובד יחד עם ה־API ב־Python (FastAPI). **סיכום שיחה (Groq)** רץ מתוך **workers** של ה-backend: טריגיר עיקרי **`task-worker`** (idle timeout); **`ai-worker`** — מאזין אופציונלי ל־`chat:completion:*` — פירוט ב־[`docs/architecture/AI.md`](../docs/architecture/AI.md).

## איך זה משתלב בפרויקט

- **תיקייה נפרדת:** `chat-ws/` ברמת שורש הפרויקט (ליד `backend/` ו־`frontend/`).
- **שני processes ל-chat:**
  - **backend (Python):** REST API, DB, שליחת הודעות (POST) + publish ל־Redis DB 1 (הודעות צ’אט, התראות צ’אט, `user:*:events`, presence וכו’); **אין כרגע** `publish` מאומת מ-Python ל־`chat:completion:*`.
  - **chat-ws (Go):** WebSocket, Subscribe ל־Redis, דחיפה ל־clients.
- **ניתוח AI:** עיקרית **`task-worker`** קורא ל־`handle_conversation_completion` (Groq → `chat_analysis`); **`ai-worker`** יכול לאותה לוגיקה אם מתקבל payload על **`chat:completion:*`** ([`AI.md`](../docs/architecture/AI.md)).
- **AI ride parsing (לא ב-chat-ws):** endpoint `POST /api/v1/passenger/passengers/ai-parse-search` מנוהל כולו ב-backend ומשמש את מסכי SearchRides/CreateRide בפרונט.

## מבנה תיקיות

```
chat-ws/
├── cmd/server/          # Entry point של שרת Go
│   └── main.go
├── internal/            # קבצי Go פנימיים
│   ├── hub/            # WebSocket Hub (מפוצל: hub.go, conn.go, handler.go, message.go)
│   ├── redis/          # Redis subscriber
│   ├── auth/           # JWT validation
│   ├── config/         # Configuration
│   └── safego/         # Panic recovery for goroutines (RecoverPanic)
└── README.md
```

## הרצה

### דרישות מוקדמות

1. **Redis** — **אותו שרת** כמו ה-backend; בדרך כלל **DB 1** לצ'אט (pub/sub, `presence:*`, ערוצים **`user:online`** / **`user:offline`**). DB 0 משמש את ה-API לדברים אחרים.
2. **משתני סביבה** (אותם כמו ב־backend, או ב־`.env` בשורש):
   - `SECRET_KEY` – אותו סוד כמו ב־Python (לאימות JWT).
   - `REDIS_URL` – למשל `redis://localhost:6379/1` (משמש ל-password ול-DB; DB 1 לצ'אט).
   - `REDIS_ADDR` – host:port לחיבור Redis ישיר (`redis:6379` ב-Compose, `localhost:6379` בהרצה ידנית).
   - `PORT` – פורט לשרת ה־WS (ברירת מחדל 8081).

### 1. שרת Go WebSocket

```bash
cd chat-ws
go mod tidy
go run cmd/server/main.go
```

או:

```bash
cd chat-ws/cmd/server
go run main.go
```

### 2. backend (Python) – כרגיל

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## חיבור מהקליינט

- **Inbound hardening (`internal/hub/handler.go` + `conn.go`):** אחרי `Upgrade` נקרא **`conn.SetReadLimit(int64(maxMessageSize))`** כאשר **`maxMessageSize = 2048`** ב־**`internal/hub/conn.go`** — פריים טקסט גדולים מהמכסה נחסמים (אבטחה/משאבים). **פריימי `typing_start`/`typing_stop`** עוברים **rate limit פר־חיבור** (`golang.org/x/time/rate`, ~30 פרסומות לשנייה, burst 60) לפני `PublishTyping` ל־Redis; חריגה — drop שקט. **`ping`** (עם `RefreshPresence`) **לא** מוגבל בקצב מתוך הלוגיקה הזו.
- **מסגרות יוצאות (batching):** לפעמים מספר JSONים נארזים למחרוזת WebSocket אחת **מופרדת ב-newline**. בפרונט — **`useUserEventStream`** (וערוצים רלוונטיים) מפרקים עם **`split('\\n')`** לפני `JSON.parse`; אחרת אירועי `user:*:events` עלולים “להיעלם” כשמשורבים עם payload אחר מאותה כתיבה.
- **`message_read`:** ה-payload שמפרסם ה-backend ל-Redis צריך לכלול **`recipient_id`** כדי ש-chat-ws ידע למי לדחוף עדכון קריאה (ראו גם **`chat-ws/ARCHITECTURE.md`**).
- **WebSocket (פיתוח):** `ws://localhost:8081/ws?token=ACCESS_TOKEN` — תואם ל־`getChatWebSocketUrl` ב־`frontend/src/config/env.ts` ב־DEV.
- **פרודקשן (דפדפן):** אותו host כמו האתר, נתיב `/ws` (דרך Nginx). ה־token הוא ה־Access Token מה־login (JWT). אותו SECRET_KEY ב־Python וב־Go.

## זרימה

### זרימת הודעות צ'אט

1. לקוח מתחבר ל־`/ws?token=...` → Go מאמת JWT ומשייך חיבור ל־user_id.
2. לקוח שולח הודעה דרך **REST** (POST ל־Python) → Python שומר ב־DB ומפרסם ל־Redis (`chat:conversation:{id}`).
3. Go מקבל מ־Redis → שולח ל־WebSocket של ה־recipient (לפי `recipient_id` ב־payload).

### זרימת ניתוח AI (מה שקיים בפועל)

1. **`task-worker`** מריץ משימות scheduled ( למשל timeout שיחה) וקורא **ישירות** ל-backend `handle_conversation_completion` (Groq → `chat_analysis` → Outbox).
2. **`ai-worker`** כולל **מאזין** אופציונלי ל־`chat:completion:*`; אין בשורות ה-Python ב-backend שזוהה **publish** לערוץ הזה — לא לבנות עליו בתור contract יציב עד שהקוד מתאים לתיעוד.
3. תוצאה נשמרת ב־DB; פרסום ל-client דרך WS לניתוח — לא חלק מ-chat-ws היום.

## Reliability & Concurrency

- **Redis reconnect:** All Redis subscribers (`RunSubscriber`, `RunUserOfflineSubscriber`, `RunUserOnlineSubscriber`) use an exponential backoff reconnect loop (1s → 30s cap) with **automatic reset after stable connections** (if the subscription ran longer than `maxBackoff`, backoff resets to 1s). If Redis disconnects, the goroutine logs a warning and re-subscribes automatically — no permanent message loss.
- **Shared `http.Client`:** outbound HTTP requests to the backend (last-seen PATCH in `flushDueLastSeen`, presence GET in `fetchLastSeenFromBackend`) use a shared `*http.Client` with a tuned `http.Transport` (`MaxIdleConns: 20`, `MaxIdleConnsPerHost: 10`, `IdleConnTimeout: 30s`) — no per-request/per-iteration client allocation.
- **Safe connection teardown:** Each `Conn` has a `done chan struct{}` guarded by `sync.Once` via `Conn.Close()`. Consumers read from `Conn.Done()` (a read-only `<-chan struct{}`). `RunWritePump` exits on `<-c.Done()` and sends a proper WebSocket `CloseNormalClosure` frame. All message senders (`SendToUser`, `broadcastOnline`, `broadcastOffline`) include `case <-c.Done():` in their select, which prevents panics from sending on a closed channel when a broadcast snapshot races with connection cleanup. The `sync.Once` guarantee means double-close panics are structurally impossible — even under concurrent teardown from the handler `defer` and hub broadcast timeout.
- **Graceful batching:** Multiple JSON payloads may be batched into a single WebSocket text frame separated by `\n`. The frontend splits on `\n` before `JSON.parse`.

## Presence ו-last seen (תקציר)

- בחיבור WS: `SET presence:{user_id}` (TTL ~60s), **`PUBLISH user:online`** (payload = `user_id`) → כל מופעי chat-ws משדרים ללקוחות `{"type":"user_online","user_id":"..."}`.
- בניתוק: מחיקת `presence`, **`PUBLISH user:offline`** → `user_offline` ב-WS; debounce + מפתחות Redis (`debounce:last_seen:*`, `last_seen:hold:*`, `last_seen:token:*`) ואז **PATCH** ל-backend `/api/v1/users/me/last-seen` → עדכון **`users.last_active_at`** (לא `last_login`).
- **HTTP** `GET /presence/{user_id}` — `online` מ-Redis; `last_seen` מה-backend (`last_active_at` עם fallback ל-`last_login`). פירוט: `docs/architecture/REALTIME.md`, `chat-ws/ARCHITECTURE.md`.

## ערוצי Redis

- `chat:conversation:{conversation_id}` – הודעות צ'אט (נשלח מ-backend, נשמע ע"י Go WS)
- `chat:typing:*` – אינדיקציית הקלדה
- **`user:*:events`** – ערוץ מאוחד לכל מסר **per-user** שעובר דרך **`SendToUser`**: (1) **`publish_user_event`** (Python); (2) אחרי התראה מה-outbox — **`WebSocketProvider`** (`invalidate`/`notifications`); (3) אחרי **`send_message`** — עדכון **unread** (`invalidate`/`unread_messages` + `count`). **אין** subscriptions ל־**`chat:notification:*`** ב־subscriber. פירוט: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **פיד התראות in-app:** רשימה מ-REST + polling ב־`useChatNotificationsFeed`; מאזין **`useUserEventStream`** ב־**`ChatContext`** (לא ב-Layout). אין WS נפרד ב-FastAPI ל־`/notifications/ws`.
- `chat:completion:{conversation_id}` – **מוכן למאזין** ב־`ai-worker`; פרסום מ-backend לא אומת בקוד הנוכחי של Python

## פיתוח

### עדכון מבנה Go

אחרי שינוי מבנה תיקיות, ודא שה-imports ב-`cmd/server/main.go` תואמים:

```go
import (
    "linkup/chat-ws/internal/auth"
    "linkup/chat-ws/internal/config"
    "linkup/chat-ws/internal/hub"
    "linkup/chat-ws/internal/redis"
    "linkup/chat-ws/internal/safego"
)
```

### ניתוח AI

טריגיר עיקרי בפועל: **`task-worker`** (משימת timeout לשיחה idle) קורא ל־`handle_conversation_completion`. **`ai-worker`** מנוי ל־`chat:completion:*` אם יתווסף publisher. הניתוח נשמר ב־**`chat_analysis`** ב־Postgres; **לא זוהה** endpoint REST ציבורי ל־`GET …/analysis` בראוטר הצ’אט — לאמת מול הריפו; ראו [`docs/architecture/AI.md`](../docs/architecture/AI.md).
