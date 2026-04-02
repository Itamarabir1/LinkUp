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
- ✅ AI analysis results (`GET /api/v1/chat/conversations/{id}/analysis`)
- ✅ Business logic
- ✅ Database operations

## AI Analysis - איפה?

**ניתוח AI רץ ב-backend worker (outbox-worker):**
- Backend מפרסם אירוע סיום שיחה ל-Redis DB 1 (`chat:completion:{conversation_id}`).
- ה-outbox-worker מאזין ל-Redis DB 1, מפעיל `handle_conversation_completion` (domain/chat/ai), שומר ל-DB ושולח ל-outbox.

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
- ✅ `backend/app/api/v1/routers/chat.py` - endpoint
- ❌ אין שירות AI נפרד; ניתוח רץ ב-backend worker

**למה לא ב-chat-ws?**
- ה-AI Analyzer Service לא צריך לייצא ללוח שנה
- הוא רק מנתח ומפרסם תוצאות
- ה-backend משתמש בתוצאות הניתוח לייצוא ללוח שנה
- שמירת קוד ב-chat-ws יוצרת code duplication מיותר

## זרימה מומלצת

### 1. שליחת הודעה
```
Client → POST /api/v1/chat/conversations/{id}/messages (backend)
       → Backend שומר ב-DB
       → Backend מפרסם ל-Redis (chat:conversation:{id})
       → chat-ws מקבל מ-Redis → שולח ל-WebSocket
       → לאחר שליחה: backend מעדכן גם **`users.last_active_at`**
       → אם הודעת סיום: Backend מפרסם ל-Redis DB 1 (chat:completion:{id})
       → outbox-worker מאזין → מנתח (AI) → שומר תוצאה + outbox
```

### 2. קבלת ניתוח AI
```
Client → GET /api/v1/chat/conversations/{id}/analysis (backend)
       → Backend קורא מ-DB/Redis
       → מחזיר תוצאה
```

### 3. ייצוא ללוח שנה
```
Client → GET /api/v1/chat/conversations/{id}/calendar.ics (backend)
       → Backend קורא הודעות מ-DB
       → Backend מנתח (או משתמש בתוצאות קיימות)
       → Backend מייצא ל-iCal
       → מחזיר קובץ .ics
```

## סיכום

| Feature | Location | Reason |
|---------|----------|--------|
| WebSocket connections | chat-ws (Go) | Real-time, performance |
| REST API endpoints | backend (Python) | Standard API pattern |
| Calendar export | backend (Python) | API endpoint |
| AI analysis | backend worker (outbox-worker) | Async, Redis DB 1 listener |
| AI analysis results API | backend (Python) | API endpoint |
| Business logic | backend (Python) | Centralized |
| Auth load testing (k6) | `backend/load_test.js` | עומס על REST register/login — לא ב-chat-ws |
