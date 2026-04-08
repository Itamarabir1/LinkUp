# Real-time Architecture

תקשורת בזמן אמת: WebSocket לסטטוס נסיעה, שרת צ'אט (Go) + Redis Pub/Sub להודעות צ'אט. **פרונט:** אימות JSON בכניסה עם **Zod** — [`frontend/src/types/wsEvents.ts`](../../frontend/src/types/wsEvents.ts) (בהתאם לחוזים למטה): אירועי נסיעה/מיקום/`UserEvent`, **והודעת צ'אט נכנסת** — `ChatMessageSchema` + מיפוי מפורש ל־[`MessageResponse`](../../frontend/src/types/api.ts) ב־[`processChatWebSocketMessage.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.ts).

**Redis — שרת אחד, שני DB לוגיים:** אותו תהליך Redis (פורט 6379); **DB 0** — backend (cache, broadcast נסיעות `ride_*`, rate limit, OTP…); **DB 1** — צ'אט + **אירועי משתמש ל-chat-ws** (pub/sub הודעות, `user:{id}:events`, `presence:*`, `user:online` / `user:offline`, completion). **חשוב:** הזרימה הפעילה ל-completion היא Redis completion channel + outbox-worker listener, לא Celery broker flow נפרד. הודעות צ'אט וגם **`publish_user_event`** מופעלים דרך **`REDIS_CHAT_URL`** / [`redis_chat_pubsub`](../../backend/app/infrastructure/redis/chat_pubsub.py) (ברירת מחדל DB **1**), כדי ש-**chat-ws** (אותו `REDIS_URL` עם `/1`) יקבל את ה-Pub/Sub. ערוצי נסיעה per-ride נשארים ב-**`broadcast`** על **`REDIS_URL`** (DB 0).

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

**אימות**: אותו JWT (SECRET_KEY) כמו ה-backend. WebSocket: `token` ב-query. **Presence ב-UI**: טעינה חד־פעמית של `GET /presence/{partner_id}`; `online` מ-Redis `presence:{user_id}`; **`last_seen`** מ-`GET /api/v1/users/{id}/last-seen` (`users.last_active_at`, עם fallback ל-`last_login`). עדכון מיידי: WS `user_online` / `user_offline` (Pub/Sub `user:online` / `user:offline`).

**Connection lifecycle**: התחברות → קבלת JWT → subscription לערוצי Redis לפי conversation. ניתוק → ניקוי מ-Hub.

**מקור**: `chat-ws/cmd/server/main.go`, `chat-ws/internal/hub/`, `chat-ws/internal/redis/subscriber.go`.

**פרונט (Vite dev):** ב־[`frontend/src/config/env.ts`](../../frontend/src/config/env.ts) — URL של צ'אט WS ב־DEV הוא `ws://localhost:8081/ws?...` (לא דרך origin של Vite). WebSocket של נסיעות/התראות ב־FastAPI: בסיס `ws://localhost:8000/api/v1`. ב־`vite.config.ts` יש proxy ל־`/api/v1`, `/ws`, `/presence` — שימושי לבקשות יחסיות; בפרודקשן הכל מאוחד דרך Nginx (`/ws`, `/presence`, `/api/v1`).

---

## Redis Pub/Sub

### Redis DB 0 (Backend / Outbox-worker)

- **Broadcast (ride updates)**: ערוץ `ride_{ride_id}` דרך `get_ride_channel` ב-`keys.py`. Backend משדר עדכוני סטטוס דרך **`publish_ride_event`** ב-[`app/infrastructure/redis/publisher.py`](../../backend/app/infrastructure/redis/publisher.py) (Pub/Sub דרך `broadcast` / DB 0); לקוחות מתחברים ל-WebSocket ב-FastAPI (`/api/v1/rides/ws/{ride_id}?token=JWT`) ומאזינים דרך `broadcaster` ל-Redis.
- **GPS — מיקום נהג לנוסעים**: ערוצים `booking_{booking_id}`. נהג שולח מיקום ב־POST /bookings/{id}/location; Backend מפרסם ל-Redis. נוסע מתחבר ל־WebSocket `/api/v1/bookings/ws/{booking_id}/location?token=JWT` ומאזין לעדכונים.
- **GPS — מיקום נוסעים לנהג**: ערוץ `ride_{ride_id}:passenger_locations`. נוסע שולח מיקום ב־POST /bookings/{id}/passenger-location; Backend מפרסם ל-Redis. נהג מתחבר ל־WebSocket `/api/v1/rides/ws/{ride_id}/passengers?token=JWT` ומאזין לעדכונים.
- **שימוש**: `app/infrastructure/redis/broadcast.py` — RedisBroadcast (Broadcast from `broadcaster`); [`app/infrastructure/location/location_service.py`](../../backend/app/infrastructure/location/location_service.py) — `broadcast_location_to_participants`, `broadcast_passenger_location_to_driver`.

### Redis DB 1 (Chat-ws + Outbox-worker)

- **הודעות צ'אט**: ערוץ `chat:conversation:{conversation_id}`. Backend (או שירות שכותב הודעות) מפרסם; chat-ws מנוי ל-pattern `chat:conversation:*` ומעביר ל-clients מחוברים.
- **התראות in-app דרך chat-ws**: pattern `chat:notification:*` (העברה ל-`SendToUser`).
- **אירועי דומיין למשתמש**: pattern `user:*:events` — ה-backend מפרסם דרך **`publish_user_event`** → [`redis_chat_pubsub.publish`](../../backend/app/infrastructure/redis/chat_pubsub.py) על **`REDIS_CHAT_URL`** (אותו DB כמו chat-ws). JSON כללי (למשל תחזוקה, סיום נסיעה); הפרונט מסנן עם **Zod** ב-[`useUserEventStream`](../../frontend/src/hooks/useUserEventStream.ts) / [`UserEventSchema`](../../frontend/src/types/wsEvents.ts). **chat-ws** נרשם ל-pattern ב-[`internal/redis/subscriber.go`](../../chat-ws/internal/redis/subscriber.go) (`UserEventPattern`) ומעביר ל-`SendToUser`.
- **Typing indicators**: ערוץ `chat:typing:*` — pattern ב-chat-ws. ה-client שולח `typing_start` / `typing_stop`, וה-Go forwarding מעביר את ה-event ל-recipient. **מבנה JSON לנמען** (כמו ב־[`chat-ws/internal/hub/message.go`](../../chat-ws/internal/hub/message.go) — `TypingPayload`): `type`, `user_id`, `conversation_id`, `recipient_id`, ואופציונלי `full_name` ב־`typing_start`. הפרונט מסנן echo למשתמש הנוכחי; בדיקות יחידה ב־[`frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts) משקפות את אותם שדות חובה.
- **Presence / last-seen** (keys ב-Redis DB=1):
  - `presence:{user_id}` — TTL 60 שנ׳ (online/offline).
  - Debounce לעדכון `last_seen` דרך backend:
    - `debounce:last_seen:{user_id}` — EX 10 שנ׳ (JWT).
    - `last_seen:hold:{user_id}` — EX 25 שנ׳.
    - `last_seen:token:{user_id}` — EX 25 שנ׳; ה-worker קורא Bearer מכאן; מחיקה רק אחרי PATCH מוצלח (כשל → ניסיון חוזר).
  - `PATCH /api/v1/users/me/last-seen` מעדכן `users.last_active_at` (שליחת הודעה בצ'אט מעדכנת גם כן).
  - **חיבור WS**: `PUBLISH user:online` (payload = `user_id`) → WS `user_online` לכל המחוברים.
  - **Disconnect**: מחיקת `presence:{user_id}`; `PUBLISH user:offline` → WS `user_offline`.
  - **חיבור מחדש** מנקה debounce/hold/token — מבטל PATCH מיותר.
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

### אימות הודעה בפרונט (Zod)

Payload של הודעה חדשה מה-WS (ללא שדה `type` של typing/presence) עובר **`ChatMessageSchema.safeParse`** — `message_id` (מספר), `conversation_id`, `sender_id`, `body`, `created_at` (מחרוזות), עם `.passthrough()` לשדות עתידיים. אחרי הצלחה נבנה אובייקט **`MessageResponse`** שדה-שדה (לא cast כפול) לפני `setMessages` / `markConversationRead`. בדיקות: [`processChatWebSocketMessage.test.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts).

---

## Broadcast (Rides)

- **ערוץ**: `ride_{ride_id}` — מוגדר ב־[`app/infrastructure/redis/keys.py`](../../backend/app/infrastructure/redis/keys.py) (`get_ride_channel`). מיקום נוסעים לנהג: `get_ride_passengers_channel`; מיקום נהג לנוסע: `get_booking_channel`.
- **מפרסם (סטטוס נסיעה)**: `publish_ride_event` ב־[`app/infrastructure/redis/publisher.py`](../../backend/app/infrastructure/redis/publisher.py) (אירועים כמו `RIDE_STARTED`, `RIDE_ENDED`, `RIDE_CANCELLED`, `RIDE_UPDATED`).
- **מפרסם (רשימת נסיעות)**: עדיין [`app/infrastructure/redis/broadcast.py`](../../backend/app/infrastructure/redis/broadcast.py) — ערוץ `rides:list` (`RIDES_LIST_CHANNEL`) לעדכוני כרטיסים ברשימה.
- **מאזין**: Client מתחבר ל־WebSocket `GET /api/v1/rides/ws/{ride_id}?token=JWT` (FastAPI); **אימות חובה** — `get_current_user_ws`. השרת נרשם ל־Redis עם אותו שם ערוץ ושולח JSON ללקוח.
- **צורת JSON ללקוח** (סטטוס נסיעה): לפחות `event`, `ride_id` (מחרוזות); לעיתים גם `status`, `color`, `message` — מקור: שירות הנסיעות + publisher.

---

## Notifications WebSocket (Backend)

- **Endpoint**: `app/domain/notifications/router.py` — `@router.websocket("/ws")` תחת prefix `/notifications` → נתיב מלא **`GET /api/v1/notifications/ws?token=JWT`**.
- **אימות**: `get_current_user_ws` ב-`app/api/dependencies/auth.py` — **רק JWT** (`decode_access_token`), מחזיר `WsUser` עם `user_id` מה-`sub` (**ללא קריאת DB** בזמן חיבור). מניעת עומס על connection pool; trade-off: אין בדיקת `is_active` ב-handshake (מול HTTP שכן טוען `User` מ-DB).
- **שימוש**: `notification_streamer.stream_user_notifications(websocket, user_id)` — Redis Pub/Sub דרך `broadcaster`, ערוץ פנימי `user_{user_id}` (מקביל נפרד מ-`user:{id}:events` שמשמש את chat-ws לדחיפות דומיין).
- **פרונט (ווב):** [`useChatNotificationsWebSocket`](../../frontend/src/context/useChatNotificationsWebSocket.ts) מעל [`useReconnectingWebSocket`](../../frontend/src/hooks/useReconnectingWebSocket.ts); **`onOpen`** מרענן פיד + unread + `linkup-notifications-refresh`. גיבוי: [`useChatNotificationsFeed`](../../frontend/src/context/useChatNotificationsFeed.ts) — REST כל **~5 דקות**.

---

## WebSocket JSON — מיקום (Backend → לקוח)

מקור: [`location_service.py`](../../backend/app/infrastructure/location/location_service.py).

- **מיקום נהג לנוסע** (ערוץ `booking_{booking_id}`): `type: "location_update"`, `ride_id`, `lat`, `lng`, אופציונלי `heading`, `speed`, `timestamp`.
- **מיקום נוסע לנהג** (ערוץ `ride_{ride_id}:passenger_locations`): `type: "passenger_location"`, `booking_id`, `passenger_id`, `lat`, `lng`, אופציונלי `ride_id`, `heading`, `speed`, `timestamp`.

הפרונט קורא את הערוצים ב־[`useDriverLocation`](../../frontend/src/hooks/useDriverLocation.ts) / [`usePassengerLocations`](../../frontend/src/hooks/usePassengerLocations.ts).

---

## GPS Tracking (מימוש)

מיקום נהג ונוסעים בזמן אמת במהלך נסיעה פעילה (סטטוס ACTIVE).

- **נהג → נוסעים**: נהג מדווח מיקום ב־POST /bookings/{booking_id}/location (body: lat, lng, heading?, speed?). Backend מפרסם לערוץ `booking_{booking_id}` לכל הבוקינגים המאושרים. נוסע מתחבר ל־WS `/bookings/ws/{booking_id}/location?token=JWT` ומקבל עדכונים.
- **נוסעים → נהג**: נוסע מדווח מיקום ב־POST /bookings/{booking_id}/passenger-location. Backend מפרסם לערוץ `ride_{ride_id}:passenger_locations`. נהג מתחבר ל־WS `/rides/ws/{ride_id}/passengers?token=JWT` ומקבל עדכונים.
- **אימות WebSocket**: `get_current_user_ws` ב־`app/api/dependencies/auth.py` — טוקן מ־query string, מאמת JWT, מחזיר `WsUser` או `None` (**ללא DB** בזמן connect).

### פרונט (ביצועים ו-UX)

קוד: [`frontend/src/hooks/useLocationBroadcast.ts`](../../frontend/src/hooks/useLocationBroadcast.ts), [`usePassengerLocationBroadcast.ts`](../../frontend/src/hooks/usePassengerLocationBroadcast.ts), [`useLocationWatcher.ts`](../../frontend/src/hooks/useLocationWatcher.ts), [`useDriverLocation.ts`](../../frontend/src/hooks/useDriverLocation.ts), [`usePassengerLocations.ts`](../../frontend/src/hooks/usePassengerLocations.ts), [`useMapMarker.ts`](../../frontend/src/hooks/useMapMarker.ts); מסכים: [`LiveMapModal`](../../frontend/src/components/LiveMapModal/index.tsx), [`LiveRideMapModal`](../../frontend/src/components/LiveRideMapModal/index.tsx).

- **שידור לשרת (POST)**: `watchPosition` + **throttle ~1.5s** (`throttleMs: 1500`) לפני `postDriverBookingLocation` / `postPassengerBookingLocation` — איזון בין רענון למספר בקשות.
- **גאולוקציה**: בשידור — `maximumAge: 0` (מיקום טרי יחסית); במודלי מפה חיה (`LiveMapModal` / `LiveRideMapModal`) לציור “אני” על המפה — `maximumAge: 1000` (פשרה מול סוללה).
- **סמני Google Maps**: `useMapMarker` יוצר `Marker` **פעם אחת** לפי `map` + אופציות, ומעדכן רק `setPosition` / `setVisible` כשהמיקום משתנה — בלי למחוק וליצור marker בכל עדכון (מונע ריצוד ועלות מיותרת).

---

סיכום “להצגה”: [`../ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md).
