# ארכיטקטורה - chat-ws vs backend

## עקרון יסוד: הפרדת אחריות

### chat-ws (Go) - WebSocket + HTTP מינימלי ל-presence
**תפקיד:** העברת הודעות real-time מ-Redis ל-WebSocket clients; **אחריות מלאה על `online`** (מפתח `presence:*` ב-Redis DB1).

**מה כן:**
- ✅ WebSocket connections management
- ✅ JWT authentication (WS + HTTP presence)
- ✅ Subscribe ל-Redis (`chat:conversation:*`, `chat:typing:*`, `chat:notification:*`, **`user:*:events`**, … + **`user:offline`** + **`user:online`**) — בחיבור: `PUBLISH user:online` → WS `user_online`; בניתוק: `user:offline` → `user_offline` (עדכון מיידי ב-UI). הודעות מ-`user:*:events` מועברות ללקוח כפי שהן (JSON) אחרי זיהוי `user_id` מהערוץ. לקוחות Redis נפרדים ל-subscribe כדי לא לחסום עם `PSubscribe` של הצ'אט
- ✅ Forward messages ל-clients
- ✅ Typing events (`typing_start` / `typing_stop`) דרך Redis (`chat:typing:*`)
- ✅ **HTTP `GET /presence/{user_id}`** — `online` מ-Redis; `last_seen` מ-backend (`GET /api/v1/users/{id}/last-seen`) כשצריך
- ✅ Presence / debounce לעדכון last-seen ב-DB:
  - `presence:{user_id}` TTL 60s
  - `debounce:last_seen:{user_id}` + `last_seen:hold:{user_id}`

**מה לא:**
- ❌ Calendar export
- ❌ AI analysis logic (רק forward אם צריך)
- ❌ Business logic

### backend (Python) - ה-API Server
**תפקיד:** כל ה-API endpoints והלוגיקה העסקית

**מה כן:**
- ✅ WebSocket ב-FastAPI לנסיעות/בוקינגים/התראות (`/api/v1/rides/...`, `/api/v1/bookings/...`, `/api/v1/notifications/ws`) — אימות ב-`get_current_user_ws`: **JWT בלבד** (`WsUser`), בלי DB בזמן connect (פרטים: `ARCHITECTURE.md` בשורש, `docs/architecture/REALTIME.md`).
- ✅ REST API endpoints
- ✅ Calendar export (`GET /api/v1/chat/conversations/{id}/calendar.ics`)
- ✅ תוצאות ניתוח AI נשמרות ב-DB (`chat_analysis`); **אין כרגע** route ייעודי ב-`backend/app/domain/chat/router.py` ל-`GET …/analysis` (סקריפטי k6 ישנים עשויים להתייחס לנתיב מתוכנן)
- ✅ Business logic
- ✅ Database operations

## AI Analysis - איפה?

**ניתוח AI רץ ב-backend worker (`ai-worker`):**
- Backend מפרסם אירוע סיום שיחה ל-Redis DB 1 (`chat:completion:{conversation_id}`).
- ה-`ai-worker` מאזין ל-Redis DB 1, מפעיל `handle_conversation_completion` (domain/chat/ai), שומר ל-DB ושולח ל-outbox.

**API Endpoint** (ב-backend):
- `GET /api/v1/chat/conversations/{id}/analysis`
- קורא תוצאות מ-DB
- מחזיר למשתמש

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
- ❌ אין microservice AI נפרד; ניתוח רץ ב-`ai-worker` מתוך backend image

**למה לא ב-chat-ws?**
- ייצוא iCal וניתוח שיחה הם לוגיקת API/DB; chat-ws הוא רק real-time fan-out
- ניתוח רץ ב-`ai-worker` אחרי `chat:completion:*`; התוצאה נשמרת ב-DB ונקראת דרך REST

## זרימה מומלצת

### 1. שליחת הודעה
```
Client → POST /api/v1/chat/conversations/{id}/messages (backend)
       → Backend שומר ב-DB
       → Backend מפרסם ל-Redis (chat:conversation:{id})
       → chat-ws מקבל מ-Redis → שולח ל-WebSocket
       → לאחר שליחה: backend מעדכן גם **`users.last_active_at`**
       → אם הודעת סיום: Backend מפרסם ל-Redis DB 1 (chat:completion:{id})
       → ai-worker מאזין → מנתח (AI) → שומר תוצאה + outbox
```

### 2. ניתוח AI (רקע)
```
ai-worker ← Redis DB1 (chat:completion:{id})
              → ניתוח (Groq) → שמירה ל-chat_analysis ב-DB
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

## התראות: שני ערוצים (חשוב)

- **`chat:notification:*` (Redis → chat-ws)** — דחיפות הקשורות ל**צ'אט**; chat-ws מנתב ללקוח על אותו חיבור WS של הצ'אט (`/ws`).
- **פיד התראות האפליקציה (מסך / באדג')** — **לא** עובר ב-chat-ws. הלקוח (ווב) מתחבר ל־**FastAPI** — **`GET /api/v1/notifications/ws?token=JWT`** — Redis Pub/Sub פנימי (`user_{user_id}`). בפרונט: `useChatNotificationsWebSocket` + גיבוי polling ב־`useChatNotificationsFeed` — ראו [`ARCHITECTURE.md`](../ARCHITECTURE.md) בשורש ו־[`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).

## סיכום

| Feature | Location | Reason |
|---------|----------|--------|
| WebSocket connections | chat-ws (Go) | Real-time, performance |
| REST API endpoints | backend (Python) | Standard API pattern |
| In-app notification **feed** WS (app bell / list) | backend (FastAPI `/notifications/ws`) | אותו מחזור חיים כמו WS נסיעות; Redis נפרד מערוצי הצ'אט |
| Chat-related notification fan-out | chat-ws (via `chat:notification:*`) | חיבור WS יחיד לשיחה |
| Calendar export | backend (Python) | API endpoint |
| AI analysis | backend worker (`ai-worker`) | Async, Redis DB 1 listener |
| AI analysis persistence | backend DB (`chat_analysis`) | worker אחרי completion |
| Business logic | backend (Python) | Centralized |
| Auth load testing (k6) | `backend/load_test.js` | עומס על REST register/login — לא ב-chat-ws |
