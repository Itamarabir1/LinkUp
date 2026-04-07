# chat-ws – WebSocket server for real-time chat

שרת WebSocket נפרד (Go) לצ'אט real-time. עובד יחד עם ה־API ב־Python (FastAPI). ניתוח AI של שיחות רץ ב-backend worker (outbox-worker).

## איך זה משתלב בפרויקט

- **תיקייה נפרדת:** `chat-ws/` ברמת שורש הפרויקט (ליד `backend/` ו־`frontend/`).
- **שני processes ל-chat:**
  - **backend (Python):** REST API, DB, שליחת הודעות (POST) + publish ל־Redis; בסיום שיחה מפרסם אירוע ל-Redis DB 1.
  - **chat-ws (Go):** WebSocket, Subscribe ל־Redis, דחיפה ל־clients.
- **ניתוח AI:** רץ ב־outbox-worker (backend): מאזין ל-Redis DB 1 לאירועי סיום שיחה, מנתח (Groq), שומר ל-DB.

## מבנה תיקיות

```
chat-ws/
├── cmd/server/          # Entry point של שרת Go
│   └── main.go
├── internal/            # קבצי Go פנימיים
│   ├── hub/            # WebSocket Hub (מפוצל: hub.go, conn.go, handler.go, message.go)
│   ├── redis/          # Redis subscriber
│   ├── auth/           # JWT validation
│   └── config/         # Configuration
└── README.md
```

## הרצה

### דרישות מוקדמות

1. **Redis** — **אותו שרת** כמו ה-backend; בדרך כלל **DB 1** לצ'אט (pub/sub, `presence:*`, ערוצים **`user:online`** / **`user:offline`**). DB 0 משמש את ה-API לדברים אחרים.
2. **משתני סביבה** (אותם כמו ב־backend, או ב־`.env` בשורש):
   - `SECRET_KEY` – אותו סוד כמו ב־Python (לאימות JWT).
   - `REDIS_URL` – למשל `redis://localhost:6379/1` (DB 1 לצ'אט).
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

- **WebSocket (פיתוח):** `ws://localhost:8081/ws?token=ACCESS_TOKEN` — תואם ל־`getChatWebSocketUrl` ב־`frontend/src/config/env.ts` ב־DEV.
- **פרודקשן (דפדפן):** אותו host כמו האתר, נתיב `/ws` (דרך Nginx). ה־token הוא ה־Access Token מה־login (JWT). אותו SECRET_KEY ב־Python וב־Go.

## זרימה

### זרימת הודעות צ'אט

1. לקוח מתחבר ל־`/ws?token=...` → Go מאמת JWT ומשייך חיבור ל־user_id.
2. לקוח שולח הודעה דרך **REST** (POST ל־Python) → Python שומר ב־DB ומפרסם ל־Redis (`chat:conversation:{id}`).
3. Go מקבל מ־Redis → שולח ל־WebSocket של ה־recipient (לפי `recipient_id` ב־payload).

### זרימת ניתוח AI (מה שקיים בפועל)

1. backend מפרסם אירוע completion ל-Redis DB 1 (`chat:completion:{conversation_id}`).
2. outbox-worker (באותו שירות backend) מאזין לערוץ completion ומריץ את ניתוח השיחה.
3. התוצאה נשמרת ב-DB; צריכה עתידית להעברה ב-WS תתווסף בנפרד אם תוגדר.

## Presence ו-last seen (תקציר)

- בחיבור WS: `SET presence:{user_id}` (TTL ~60s), **`PUBLISH user:online`** (payload = `user_id`) → כל מופעי chat-ws משדרים ללקוחות `{"type":"user_online","user_id":"..."}`.
- בניתוק: מחיקת `presence`, **`PUBLISH user:offline`** → `user_offline` ב-WS; debounce + מפתחות Redis (`debounce:last_seen:*`, `last_seen:hold:*`, `last_seen:token:*`) ואז **PATCH** ל-backend `/api/v1/users/me/last-seen` → עדכון **`users.last_active_at`** (לא `last_login`).
- **HTTP** `GET /presence/{user_id}` — `online` מ-Redis; `last_seen` מה-backend (`last_active_at` עם fallback ל-`last_login`). פירוט: `docs/architecture/REALTIME.md`, `chat-ws/ARCHITECTURE.md`.

## ערוצי Redis

- `chat:conversation:{conversation_id}` – הודעות צ'אט (נשלח מ-backend, נשמע ע"י Go WS)
- `chat:typing:*` – אינדיקציית הקלדה
- `chat:notification:*` – דחיפות in-app לפי נמען
- **`user:*:events`** – אירועי דומיין מה-backend (`publish_user_event` דרך **`REDIS_CHAT_URL`** / DB כמו chat-ws, לא `broadcast`/DB0); Go מנתב ל-`SendToUser` לפי מזהה מהערוץ. הקבוע בקוד: `UserEventPattern` ב-`internal/redis/subscriber.go`
- `chat:completion:{conversation_id}` – טריגר לניתוח AI בצד worker

## פיתוח

### עדכון מבנה Go

אחרי שינוי מבנה תיקיות, ודא שה-imports ב-`cmd/server/main.go` תואמים:

```go
import (
    "linkup/chat-ws/internal/auth"
    "linkup/chat-ws/internal/config"
    "linkup/chat-ws/internal/hub"
    "linkup/chat-ws/internal/redis"
)
```

### ניתוח AI

ניתוח AI של שיחות רץ ב-backend (outbox-worker). לבדיקה: הרץ את ה-worker והפעל סיום שיחה מהאפליקציה; התוצאות נשמרות ב-DB ונגישות ב-`GET /api/v1/chat/conversations/{id}/analysis`.
