# Real-time Architecture

תקשורת בזמן אמת: WebSocket לסטטוס נסיעה, שרת צ'אט (Go) + Redis Pub/Sub להודעות צ'אט.

**Redis — שרת אחד, שני DB לוגיים:** אותו תהליך Redis (פורט 6379); **DB 0** — backend (cache, broadcast נסיעות, rate limit, OTP…); **DB 1** — צ'אט (pub/sub הודעות, `presence:*`, ערוץ `user:offline`, completion). **חשוב:** ה-backend מפרסם הודעות צ'אט ל-`REDIS_CHAT_URL` (ברירת מחדל DB **1**). **chat-ws חייב להשתמש באותו מספר DB** (`REDIS_URL` בסודות K8s — למשל `.../1`). אם ה-backend על DB 0 ו-chat-ws על DB 1, הודעות לא יגיעו ב-WebSocket עד רענון.

---

## WebSocket Server (Chat) — Go

| פריט | ערך |
|------|------|
| שירות | chat-ws |
| path | chat-ws/ |
| שפה | Go |
| פורט | 8081 (משתנה ב-PORT) |
| Endpoint WS | `GET /ws?token=<JWT>` |
| Endpoint HTTP (presence) | `GET /presence/{user_id}` — Header `Authorization: Bearer <JWT>` |

**אימות**: אותו JWT (SECRET_KEY) כמו ה-backend. WebSocket: `token` ב-query. **Presence ב-UI**: הפרונט קורא **ישירות ל-chat-ws** (`GET /presence/{partner_id}`); `online` נגזר מ-`EXISTS presence:{user_id}` ב-Redis DB1 בלבד. **`last_seen`** ב-JSON מגיע מ-`GET /api/v1/users/{id}/last-seen` ב-backend (שדה `users.last_login`) — ה-backend **לא** קורא מפתחות `presence:*` ב-Redis.

**Connection lifecycle**: התחברות → קבלת JWT → subscription לערוצי Redis לפי conversation. ניתוק → ניקוי מ-Hub.

**מקור**: `chat-ws/cmd/server/main.go`, `chat-ws/internal/hub/`, `chat-ws/internal/redis/subscriber.go`.

**פרונט (Vite dev):** ב־[`frontend/src/config/env.ts`](../../frontend/src/config/env.ts) — URL של צ'אט WS ב־DEV הוא `ws://localhost:8081/ws?...` (לא דרך origin של Vite). WebSocket של נסיעות/התראות ב־FastAPI: בסיס `ws://localhost:8000/api/v1`. ב־`vite.config.ts` יש proxy ל־`/api/v1`, `/ws`, `/presence` — שימושי לבקשות יחסיות; בפרודקשן הכל מאוחד דרך Nginx (`/ws`, `/presence`, `/api/v1`).

---

## Redis Pub/Sub

### Redis DB 0 (Backend / Outbox-worker)

- **Broadcast (ride updates)**: ערוצים `ride_{ride_id}`. Backend מפרסם עדכון; לקוחות מתחברים ל-WebSocket ב-FastAPI (`/api/v1/rides/ws/{ride_id}`) ומאזינים דרך `broadcaster` ל-Redis.
- **GPS — מיקום נהג לנוסעים**: ערוצים `booking_{booking_id}`. נהג שולח מיקום ב־POST /bookings/{id}/location; Backend מפרסם ל-Redis. נוסע מתחבר ל־WebSocket `/api/v1/bookings/ws/{booking_id}/location?token=JWT` ומאזין לעדכונים.
- **GPS — מיקום נוסעים לנהג**: ערוץ `ride_{ride_id}:passenger_locations`. נוסע שולח מיקום ב־POST /bookings/{id}/passenger-location; Backend מפרסם ל-Redis. נהג מתחבר ל־WebSocket `/api/v1/rides/ws/{ride_id}/passengers?token=JWT` ומאזין לעדכונים.
- **שימוש**: `app/infrastructure/redis/broadcast.py` — RedisBroadcast (Broadcast from `broadcaster`); `app/services/location/location_service.py` — broadcast_location_to_participants, broadcast_passenger_location_to_driver.

### Redis DB 1 (Chat-ws + Outbox-worker)

- **הודעות צ'אט**: ערוץ `chat:conversation:{conversation_id}`. Backend (או שירות שכותב הודעות) מפרסם; chat-ws מנוי ל-pattern `chat:conversation:*` ומעביר ל-clients מחוברים.
- **Typing indicators**: ערוץ `chat:typing:*` — pattern ב-chat-ws. ה-client שולח `typing_start` / `typing_stop`, וה-Go forwarding מעביר את ה-event ל-recipient.
- **Presence / last-seen** (keys ב-Redis DB=1):
  - `presence:{user_id}` — TTL 60 שנ׳ (online/offline).
  - Debounce לעדכון `last-seen` דרך backend:
    - `debounce:last_seen:{user_id}` — EX 10 שנ׳ (מכיל token).
    - `last_seen:hold:{user_id}` — EX 25 שנ׳ (מכיל token עד שה-debounce פג).
  - ה-Go שולח `PATCH /api/v1/users/me/last-seen`, שמעדכן בפועל את `users.last_login` (מוצג בפרונט כ-`last_seen`).
  - **Disconnect (סגירת WS)**: מחיקת `presence:{user_id}`; **`PUBLISH user:offline`** (payload = `user_id`) — כל מופעי chat-ws מקבלים; שידור WS `{"type":"user_offline","user_id":"..."}` לכל הלקוחות המחוברים → הפרונט מעדכן **מיידית** “לא מחובר” לשותף (בנוסף לפולינג ל-`GET /presence/...` כגיבוי).
  - יצירת מפתחות debounce/hold כדי לעדכן last-seen רק אחרי ~10s בלי reconnect. **חיבור מחדש** מוחק את מפתחות ה-debounce — מבטל PATCH מיותר.
- **Chat completion**: ערוץ `chat:completion:*`. כששיחה "נגמרת" (מהפרונט/backend) מפרסמים אירוע; outbox-worker מאזין ב-Redis DB 1 ומפעיל ניתוח AI (Groq) ושמירה ל-DB + אופציונלי outbox.

---

## Chat Flow

```
Client A (נהג)                Backend API                    Redis DB 1              chat-ws (Go)              Client B (נוסע)
     |                              |                              |                          |                          |
     |  POST /chat/.../messages     |                              |                          |                          |
     | -------------------------->  |  PUBLISH chat:conversation:X |                          |                          |
     |                              | -------------------------->  |  PMESSAGE                |                          |
     |                              |                              | -----------------------> |  forward to Client B      |
     |                              |                              |                          | -------------------------->|
```

- **כתיבת הודעה**: POST ל-FastAPI → שמירה ב-DB → publish ל-Redis `chat:conversation:{id}` → chat-ws מקבל ומעביר ל-clients המנויים.
- **קבלת הודעה**: Client מחובר ל-chat-ws עם JWT; chat-ws נרשם ל-conversation הרלוונטי; הודעות מגיעות ב-WebSocket.

---

## Broadcast (Rides)

- **ערוץ**: `ride_{ride_id}`.
- **מפרסם**: Backend (למשל אחרי עדכון סטטוס נסיעה) — `broadcast.publish(channel, message)`.
- **מאזין**: Client מתחבר ל-WebSocket `GET /api/v1/rides/ws/{ride_id}` (FastAPI); השרת משתמש ב-`broadcast.subscribe(channel)` ושולח כל הודעה ל-WebSocket.

---

## Notifications WebSocket (Backend)

- **Endpoint**: ראוטר ב-`app/api/websockets/notifications.py` — WebSocket `/ws` עם אימות JWT (get_current_user_ws).
- **שימוש**: `notification_service.stream_user_notifications(websocket, user_id)` — stream של התראות למשתמש מחובר.
- **רישום**: אם הראוטר רשום ב-app (למשל תחת prefix מסוים), הנתיב המלא תלוי ב-include_router.

---

## GPS Tracking (מימוש)

מיקום נהג ונוסעים בזמן אמת במהלך נסיעה פעילה (סטטוס ACTIVE).

- **נהג → נוסעים**: נהג מדווח מיקום ב־POST /bookings/{booking_id}/location (body: lat, lng, heading?, speed?). Backend מפרסם לערוץ `booking_{booking_id}` לכל הבוקינגים המאושרים. נוסע מתחבר ל־WS `/bookings/ws/{booking_id}/location?token=JWT` ומקבל עדכונים.
- **נוסעים → נהג**: נוסע מדווח מיקום ב־POST /bookings/{booking_id}/passenger-location. Backend מפרסם לערוץ `ride_{ride_id}:passenger_locations`. נהג מתחבר ל־WS `/rides/ws/{ride_id}/passengers?token=JWT` ומקבל עדכונים.
- **אימות WebSocket**: `get_current_user_ws` ב־`app/api/dependencies/auth.py` — טוקן מ־query string, מחזיר User או None.

---

סיכום “להצגה”: [`../ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md).
