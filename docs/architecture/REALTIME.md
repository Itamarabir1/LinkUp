# Real-time Architecture

תקשורת בזמן אמת: WebSocket לסטטוס נסיעה, שרת צ'אט (Go) + Redis Pub/Sub להודעות צ'אט. **פרונט:** אימות JSON בכניסה עם **Zod** — [`frontend/src/types/wsEvents.ts`](../../frontend/src/types/wsEvents.ts) (בהתאם לחוזים למטה): אירועי נסיעה/מיקום/`UserEvent`, **והודעת צ'אט נכנסת** — `ChatMessageSchema` + מיפוי מפורש ל־[`MessageResponse`](../../frontend/src/types/api.ts), ואז **`applyInboundRealMessage`** על רשימת **[`ChatListRow`](../../frontend/src/types/chatList.ts)** (מיזוג עם **`appendMessageDedupById`**) ב־[`processChatWebSocketMessage.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.ts) — כולל ניתור **`outboundPendingRef`** להודעות יוצאות אופטימיות (לפני/אחרי תשובת REST).

**Redis — שרת אחד, שני DB לוגיים:** אותו תהליך Redis (פורט 6379); **DB 0** — backend (cache, broadcast נסיעות `ride_*`, rate limit, OTP…); **DB 1** — צ'אט + **אירועי משתמש ל-chat-ws** (pub/sub הודעות, `user:{id}:events`, `presence:*`, `user:online` / `user:offline`; וגם תבנית **`chat:completion:*`** למאזין ב־**`ai-worker`** — **ללא** `publish` מאומת מה-backend לאותה תבנית). **חשוב:** **סיכום שיחה (Groq)** בפועל מופעל מ־**`task-worker`** (idle timeout → `handle_conversation_completion` → `chat_analysis` + Outbox) — לא דרך ערוץ ה-Redis הזה; המאזין ב־**`ai-worker`** אופציונלי ([`AI.md`](AI.md)). לא Celery broker flow נפרד. הודעות צ'אט וגם **`publish_user_event`** מופעלים דרך **`REDIS_CHAT_URL`** / [`redis_chat_pubsub`](../../backend/app/infrastructure/redis/chat_pubsub.py) (ברירת מחדל DB **1**), כדי ש-**chat-ws** יקבל את ה-Pub/Sub. בפרודקשן, מקור הסיסמה של `chat-ws` מגיע מה-root compose env (`REDIS_PASSWORD`) דרך `REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1` ב־[`docker-compose.yml`](../../docker-compose.yml) — לא סיסמה hardcoded ב־`chat-ws/.env`. ערוצי נסיעה per-ride נשארים ב-**`broadcast`** על **`REDIS_URL`** (DB 0).

**Recent updates (important):**
- Missed chat messages: on each chat WebSocket **`onopen`**, the web client runs **`fetchMissedGap`** (**[`fetchMissedGap.ts`](../../frontend/src/pages/MessageThread/fetchMissedGap.ts)**) backed by **`GET /chat/conversations/{id}/messages`**: **`after=`** **`max(confirmed message_id)`** or **`after=0`** when there is no local anchor (`lastMessageIdRef` is **`null`**). If **`has_more`**, follow-up HTTP calls use **`before=next_cursor`** (same pagination as scrolling older messages) until **`has_more` is false** or a **hard cap (~50 pages, `limit` 30 per request)** — with **retry** per page — so bursts during disconnect wider than **30** messages still load instead of silently dropping the tail (extreme bursts may remain partial). Wired from **`useChatWebSocket.ts`** (**`fetchMissedMessages(lastMessageIdRef ?? 0)`**) and **`useConversationMessages.ts`** (**`lastMessageIdRef`** = max **`message_id`** over **confirmed** [`ChatListRow`](../../frontend/src/types/chatList.ts) rows only; pending optimistic tail is excluded from the max and preserved when merging). Merged rows dedupe by **`message_id`** via **`applyInboundRealMessage`**; abort if **`conversation_id`** changes mid-backfill (**`cidRef`** / **`shouldAbort`**).
- Read receipts are persisted with a DB-level message cursor (`conversation_participants.last_read_message_id`) and broadcast as `message_read` events with `read_up_to_message_id`.
- Notification refresh events are unified on `chat-ws` (`user:*:events`) to reduce parallel socket usage.
- **Redis subscriber resilience (chat-ws):** all three Redis subscribers (`RunSubscriber` for chat/typing/user-events, `RunUserOfflineSubscriber`, `RunUserOnlineSubscriber`) wrap their subscribe logic in a **reconnect loop with exponential backoff** (1s initial, doubling to 30s cap). A transient Redis disconnect no longer kills the subscriber goroutine permanently — it logs a warning and reconnects automatically. Implementation: `subscriber.go` extracts `runOnce`; `hub.go` extracts `runUserOfflineOnce`/`runUserOnlineOnce`.
- **Connection teardown safety (chat-ws):** each `Conn` carries a `done chan struct{}` protected by `sync.Once` via `Conn.Close()`. `RunWritePump` listens on `Conn.Done()` (read-only `<-chan struct{}`) to exit cleanly with a proper `CloseNormalClosure` frame. All senders (`SendToUser`, `broadcastOnline`, `broadcastOffline`) include `<-c.Done()` in their `select` — preventing send-on-closed-channel panics when a broadcast snapshot races with connection teardown. The `sync.Once` wrapper makes double-close panics structurally impossible under concurrent teardown.
- **chat-ws operational hardening (H7–H11):**
  - **`/healthz` endpoint** verifies Redis PING + subscriber goroutine liveness via atomic timestamps (`Hub.SubscribersHealthy()`). Each subscriber marks alive on successful `(P)Subscribe`; staleness threshold 2 min. Returns 503 with structured detail (`redis unreachable` or `subscriber stale`).
  - **Graceful shutdown:** `*http.Server` + `srv.Shutdown(10s)` drains active connections on SIGTERM.
  - **Pong/read deadline:** `SetReadDeadline(pongWait=60s)` + `SetPongHandler` on each connection. Dead clients that stop responding to pings are detected and cleaned up within 60s — no more leaked goroutines.
  - **Panic recovery:** `defer safego.RecoverPanic(component, op)` on every independent goroutine via shared `internal/safego` package. Logs panic + stack trace without crashing the process.
- **Frontend WebSocket reconnect:** delays use **`computeReconnectDelayMs`** in **[`reconnectBackoff.ts`](../../frontend/src/utils/reconnectBackoff.ts)** — exponential backoff from **3s** (±20% jitter), doubling each attempt, **30s** cap — wired in **[`useChatWebSocket.ts`](../../frontend/src/pages/MessageThread/useChatWebSocket.ts)**, **[`useReconnectingWebSocket.ts`](../../frontend/src/hooks/useReconnectingWebSocket.ts)**, **[`useReconnectingWebSocketState.ts`](../../frontend/src/hooks/useReconnectingWebSocketState.ts)**; the attempt counter resets on **`onopen`** and when **`cid` / `reconnectKey`** changes (new effect run).
- **Frontend WebSocket token freshness gate:** before every reconnect attempt, **`ensureFreshToken()`** ([`tokenRefresh.ts`](../../frontend/src/api/tokenRefresh.ts)) decodes the JWT `exp` claim client-side ([`tokenUtils.ts`](../../frontend/src/utils/tokenUtils.ts)); if the access token is expired or < 60s from expiry, a coordinated refresh runs (`POST /auth/refresh` via HttpOnly cookie) before the `new WebSocket(url)` call. The refresh is single-flight: multiple concurrent callers (WS hooks + Axios interceptor) share the same in-flight request. If refresh fails, `auth:session-expired` fires and reconnect stops.
- **Frontend visibility-aware reconnect:** all three WebSocket hooks (`useReconnectingWebSocket`, `useReconnectingWebSocketState`, `useChatWebSocket`) listen for the **`visibilitychange`** event. When the tab returns to the foreground and no WebSocket is open, the hook triggers an **immediate** reconnect (attempt counter reset to 0) with a freshly validated token — skipping the exponential backoff delay that would otherwise apply.

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
| Endpoint HTTP (health) | `GET /healthz` — checks Redis PING + subscriber liveness (`SubscribersHealthy`); returns `200 {"status":"ok"}` or `503 {"status":"unhealthy","detail":"..."}` |

**אימות**: אותו JWT (SECRET_KEY) כמו ה-backend. WebSocket: `token` ב-query. **Presence ב-UI**: טעינה חד־פעמית של `GET /presence/{partner_id}`; `online` מ-Redis `presence:{user_id}`; **`last_seen`** מ-`GET /api/v1/users/{id}/last-seen` (`users.last_active_at`, עם fallback ל-`last_login`). עדכון מיידי: WS `user_online` / `user_offline` (Pub/Sub `user:online` / `user:offline`).

**Connection lifecycle**: התחברות → קבלת JWT → subscription לערוצי Redis לפי conversation. ניתוק → ניקוי מ-Hub.

**מקור**: `chat-ws/cmd/server/main.go`, `chat-ws/internal/hub/`, `chat-ws/internal/redis/subscriber.go`.

**פרונט (Vite dev):** ב־[`frontend/src/config/env.ts`](../../frontend/src/config/env.ts) — URL של צ'אט WS ב־DEV הוא `ws://localhost:8081/ws?...` (לא דרך origin של Vite). WebSocket של נסיעות/התראות ב־FastAPI: בסיס `ws://localhost:8000/api/v1`. ב־`vite.config.ts` יש proxy ל־`/api/v1`, `/ws`, `/presence` — שימושי לבקשות יחסיות; בפרודקשן הכל מאוחד דרך Nginx (`/ws`, `/presence`, `/api/v1`).

---

## Redis Pub/Sub

### Redis DB 0 (Backend / infra workers)

- **Broadcast (ride updates)**: ערוץ `ride_{ride_id}` דרך `get_ride_channel` ב-`keys.py`. Backend משדר עדכוני סטטוס דרך **`publish_ride_event`** ב-[`app/infrastructure/redis/publisher.py`](../../backend/app/infrastructure/redis/publisher.py) (Pub/Sub דרך `broadcast` / DB 0); לקוחות מתחברים ל-WebSocket ב-FastAPI (`/api/v1/rides/ws/{ride_id}?token=JWT`) ומאזינים דרך `broadcaster` ל-Redis.
- **GPS — מיקום נהג לנוסעים**: ערוצים `booking_{booking_id}`. נהג שולח מיקום ב־POST /bookings/{id}/location; Backend מפרסם ל-Redis. נוסע מתחבר ל־WebSocket `/api/v1/bookings/ws/{booking_id}/location?token=JWT` ומאזין לעדכונים.
- **GPS — מיקום נוסעים לנהג**: ערוץ `ride_{ride_id}:passenger_locations`. נוסע שולח מיקום ב־POST /bookings/{id}/passenger-location; Backend מפרסם ל-Redis. נהג מתחבר ל־WebSocket `/api/v1/rides/ws/{ride_id}/passengers?token=JWT` ומאזין לעדכונים.
- **שימוש**: `app/infrastructure/redis/broadcast.py` — RedisBroadcast (Broadcast from `broadcaster`); [`app/infrastructure/location/location_service.py`](../../backend/app/infrastructure/location/location_service.py) — `broadcast_location_to_participants`, `broadcast_passenger_location_to_driver`.

### Redis DB 1 (chat-ws + ai-worker)

- **הודעות צ'אט**: ערוץ `chat:conversation:{conversation_id}`. ה-API כותב `chat.message_sent` ל-`outbox_events` באותה טרנזקציה של ההודעה; `notification-worker` (`run_outbox_worker`) מפעיל `RedisChatPublisher` ומפרסם ל-Redis, ו-`chat-ws` מנוי ל-pattern `chat:conversation:*` ומעביר ל-clients מחוברים.
- **אירועים per-user על אותו namespace (DB1)**: pattern **`user:*:events`** — מאחד:
  - **`publish_user_event`** (דומיין נסיעות/בוקינגים וכו') → JSON בפורмат **`UserEvent`**;
  - אחרי שליחת התראות outbox, **[`WebSocketProvider`](../../backend/app/domain/notifications/providers/websocket_provider.py)** מפרסם **`{ type: "invalidate", resource: "notifications", event, user_id }`** לרענון פיד in-app;
  - לאחר **`send_message`** בצ'אט, **[`chat/service.py`](../../backend/app/domain/chat/service.py)** מפרסם **`{ type: "invalidate", resource: "unread_messages", count }`** לעדכון באדג' unread בלי להמתין ל-polling.
- **פרונט:** [`useUserEventStream`](../../frontend/src/hooks/useUserEventStream.ts) על אותו חיבור chat-ws — קודם **`InvalidateEventSchema`**, אחר כך **`UserEventSchema`**; הלוגיקה ב-[`ChatContext.tsx`](../../frontend/src/context/ChatContext.tsx): **`unread_messages`** → **`setUnreadDirect`** (או invalidate) ל־RQ; **`notifications`** → **`refreshUnreadNotifications`**, אירוע **`NOTIFICATIONS_REFRESH_EVENT`**, ובתנאי שדות מהשרת — **`linkup:user-event`** עם `{ event, user_id }` (תאימות מסכים קיימים). פריימי **`unread_count`** על ערוץ השיחה נשארים ב־[**`ChatPresenceEventSchema`**](../../frontend/src/types/wsEvents.ts) / **`processChatWebSocketMessage`** — ללא שינוי במסלול הזה לטובת הריפקטור. **`useLayoutShell`** לא מחזיק מאזין WS; הוא רק מזין את ה־Navbar מתוך `ChatContext` (תגית מספרית + מחלקת **`.iconBtnUnread`** ב־`Layout` כשיש ספירה חיובית).
- **chat-ws:** [`internal/redis/subscriber.go`](../../chat-ws/internal/redis/subscriber.go) — `PSubscribe` על **`chat:conversation:*`**, **`chat:typing:*`**, **`user:*:events`** בלבד (**אין** `chat:notification:*`).
- **Typing indicators**: ערוץ `chat:typing:*` — pattern ב-chat-ws. ה-client שולח `typing_start` / `typing_stop`, וה-hub ב-Go מפרסם ל-Redis עם **rate limit פר־חיבור** (ברירת מחדל: ~30 פרסומות/שנייה, burst 60; **`ping`** לא נכלל); גודל מסר טקסט נכנס מוגבל ב־**`SetReadLimit(2048)`**. ה-forwarding לנמען כמו קודם. **מבנה JSON לנמען** (כמו ב־[`chat-ws/internal/hub/message.go`](../../chat-ws/internal/hub/message.go) — `TypingPayload`): `type`, `user_id`, `conversation_id`, `recipient_id`, ואופציונלי `full_name` ב־`typing_start`. הפרונט מסנן echo למשתמש הנוכחי; בדיקות יחידה ב־[`frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts) משקפות את אותם שדות חובה.
- **Read receipts**: payload `message_read` כולל `conversation_id`, `reader_id`, ואופציונלית `read_up_to_message_id`; **חובה `recipient_id`** — מזהה הצד השני בשיחה 1:1 (מי שיש לו לקבל את הפריים על ה־WS). אותו שדה כמו בהודעת צ'אט שנשלחת על `chat:conversation:*`, כי ב־[`chat-ws`](../../chat-ws/internal/hub/handler.go) הניתוב ל־[`PublishChatMessage`](../../chat-ws/internal/hub/handler.go) קורא `recipient_id` מתוך ה־JSON. הערך `read_up_to_message_id` מגיע מ־`ConversationParticipant.last_read_message_id` של הקורא; ה־frontend מתייחס אליו כ־monotonic read cursor ל־`✓✓`.
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
- **Chat completion / AI לאחר סיום שיחה:**
  - **מסלול מתוזמן (מימוש בשורות Python הנוכחי):** משימות מתוך **`task-worker`** (למשל `execute_chat_timeout_job` ב־`chat_timeout_task.py`) קוראות **ישירות** ל־`handle_conversation_completion` עם DB — ניתוח **Groq** דרך `asyncio.to_thread` (non-blocking, לא חוסם את ה-event loop), כתיבה ל־`chat_analysis`, ואז **`publish_to_outbox`** לאירוע התראות. פירוט: [`AI.md`](AI.md).
  - **מסלול Redis (מימוש מאזין בלבד):** `ai-worker` רץ **`run_chat_completion_redis_listener`** על תבנית **`chat:completion:*`** (`REDIS_CHAT_URL`). **לא זוהה ב־`backend/` פרסום** לערוץ זה — אם מוסיפים טריגר Redis בעתיד, יישור הניסוח עם `chat-ws`/`REALTIME.md` חובה.
- **AI ride parsing endpoint**: `POST /api/v1/passenger/passengers/ai-parse-search` (ל-SearchRides/CreateRide) הוא REST בלבד דרך backend ואינו חלק מנתיבי WS/PubSub של chat-ws.

---

## Chat Flow

```
Client A (נהג)                Backend API           notification-worker            Redis DB 1              chat-ws (Go)              Client B (נוסע)
     |                              |                              |                          |                          |                          |
     |  POST /chat/.../messages     |                              |                          |                          |                          |
     | -------------------------->  |  DB write + outbox event     |                          |                          |                          |
     |                              | -------------------------->  |  PUBLISH chat:conversation:X |                      |                          |
     |                              |                              | -----------------------> |  PMESSAGE                |                          |
     |                              |                              |                          | -----------------------> |  forward to Client B      |
     |                              |                              |                          |                          | -------------------------->|
```

- **כתיבת הודעה**: POST ל-FastAPI → שמירה ב-DB + Outbox event (`chat.message_sent`) באותה טרנזקציה → notification-worker (`run_outbox_worker`) מפרסם ל-Redis `chat:conversation:{id}` → chat-ws מקבל ומעביר ל-clients המנויים.
- **קבלת הודעה**: Client מחובר ל-chat-ws עם JWT; chat-ws נרשם ל-conversation הרלוונטי; הודעות מגיעות ב-WebSocket.
- **קריאה (read receipt)**: כניסה לשיחה או קבלת הודעה מפעילות `mark_conversation_read`, שמעכנת גם `last_read_at` וגם `last_read_message_id`. לאחר מכן backend מפרסם `message_read` עם `read_up_to_message_id`, והצד השני צובע כ־read כל הודעה יוצאת עד ה־cursor הזה.
- **השלמת הודעות אחרי ניתוק / פתיחה מחדש של ה־WS**: REST עם **`after`** לעמוד הראשון, ואחר כך (**אם צריך**) **`before=next_cursor`** לפי חוזה ה־API (ראו **`docs/architecture/API.md`**) עד שהפער נסגר או שנפגע **תקרת עמודים בצד הלקוח** (~50 בקשות). העוגן הוא מקסימום ה־`message_id` שכבר ב־state, או **`after=0`** כשאין עדיין עוגן מקומי (אז השרת מחזיר הודעות עם **`message_id > 0`** לפי אותו מסנן ב־CRUD).

### אימות הודעה בפרונט (Zod)

Payload של הודעה חדשה מה-WS (ללא שדה `type` של typing/presence) עובר **`ChatMessageSchema.safeParse`** — `message_id` (מספר), `conversation_id`, `sender_id`, `body`, `created_at` (מחרוזות), עם `.passthrough()` לשדות עתידיים. אחרי הצלחה נבנה אובייקט **`MessageResponse`** שדה-שדה (לא cast כפול) לפני עדכון state: **`setMessages`** מקבל פונקציה שמריצה **`applyInboundRealMessage`**, שמסירה שורת **`pending`** מתואמת (כשהשולח הוא המשתמש הנוכחי ויש **`outboundPendingRef`**) ואז **`appendMessageDedupById`** על שכבת ה-**confirmed**. **`markConversationRead`** נשאר כמו קודם. בדיקות: [`processChatWebSocketMessage.test.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.test.ts).

---

## Broadcast (Rides)

- **ערוץ**: `ride_{ride_id}` — מוגדר ב־[`app/infrastructure/redis/keys.py`](../../backend/app/infrastructure/redis/keys.py) (`get_ride_channel`). מיקום נוסעים לנהג: `get_ride_passengers_channel`; מיקום נהג לנוסע: `get_booking_channel`.
- **מפרסם (סטטוס נסיעה)**: `publish_ride_event` ב־[`app/infrastructure/redis/publisher.py`](../../backend/app/infrastructure/redis/publisher.py) (אירועים כמו `RIDE_STARTED`, `RIDE_ENDED`, `RIDE_CANCELLED`, `RIDE_UPDATED`).
- **מפרסם (רשימת נסיעות)**: עדיין [`app/infrastructure/redis/broadcast.py`](../../backend/app/infrastructure/redis/broadcast.py) — ערוץ `rides:list` (`RIDES_LIST_CHANNEL`) לעדכוני כרטיסים ברשימה.
- **מאזין**: Client מתחבר ל־WebSocket `GET /api/v1/rides/ws/{ride_id}?token=JWT` (FastAPI); **אימות חובה** — `get_current_user_ws`. השרת נרשם ל־Redis עם אותו שם ערוץ ושולח JSON ללקוח.
- **צורת JSON ללקוח** (סטטוס נסיעה): לפחות `event`, `ride_id` (מחרוזות); לעיתים גם `status`, `color`, `message` — מקור: שירות הנסיעות + publisher.

---

## התראות in-app (רשימה + רענון בזמן אמת)

- **REST — מקור הרשימה:** **`GET /api/v1/users/me/notifications`** (ראו [`API.md`](API.md)) עם cursor pagination (`limit`, `after`, `next_cursor`, `has_more`). בפרונט: מסך התראות ב-`useInfiniteQuery`; באדג'ים ב-`useChatNotificationsFeed` על עמוד ראשון (`limit=20`) עם **refetch** כל ~5 דקות.
- **אין** כרגע WebSocket ייעודי ב-FastAPI ל־`/api/v1/notifications/ws` — הקובץ [`app/domain/notifications/router.py`](../../backend/app/domain/notifications/router.py) ריק ולא נרשם ב־[`api_router.py`](../../backend/app/api/v1/api_router.py).
- **דחיפת רענון (סיכום):** אותו ערוץ **`user:{user_id}:events`**. תבנית **`invalidate`** לרענון UI (התראות + unread); תבנית **`UserEvent`** מ־`publish_user_event`. פירוט מלא בפסקה על Redis DB1 למעלה; polling ל-REST נשאר גיבוי.

---

## WebSocket JSON — מיקום (Backend → לקוח)

מקור: [`location_service.py`](../../backend/app/infrastructure/location/location_service.py).

- **מיקום נהג לנוסע** (ערוץ `booking_{booking_id}`): `type: "location_update"`, `ride_id`, `lat`, `lng`, אופציונלי `heading`, `speed`, `timestamp`.
- **מיקום נוסע לנהג** (ערוץ `ride_{ride_id}:passenger_locations`): `type: "passenger_location"`, `booking_id`, `passenger_id`, `lat`, `lng`, אופציונלי `ride_id`, `heading`, `speed`, `timestamp`.

הפרונט קורא את הערוצים ב־[`useDriverLocation`](../../frontend/src/hooks/useDriverLocation.ts) / [`usePassengerLocations`](../../frontend/src/hooks/usePassengerLocations.ts).

---

## GPS Tracking (מימוש)

מיקום נהג ונוסעים בזמן אמת במהלך נסיעה פעילה (סטטוס ACTIVE).

- **נהג → נוסעים**: נהג מדווח מיקום ב־POST /bookings/{booking_id}/location (body: lat, lng, heading?, speed?). **לוגיקת הרשאות וסטטוס נסיעה** ב־`BookingLocationService.broadcast_driver_location` ב־[`location_service.py`](../../backend/app/domain/bookings/location_service.py) (הראוטר רק מעביר לשירות). Backend מפרסם לערוץ `booking_{booking_id}` לכל הבוקינגים המאושרים. נוסע מתחבר ל־WS **`GET /api/v1/bookings/ws/{booking_id}/location?token=JWT`** ומקבל עדכונים.
- **נוסעים → נהג**: נוסע מדווח מיקום ב־POST /bookings/{booking_id}/passenger-location. **אימות בעלות על ההזמנה** ב־`BookingLocationService.broadcast_passenger_location` באותו קובץ. Backend מפרסם לערוץ `ride_{ride_id}:passenger_locations`. נהג מתחבר ל־WS **`GET /api/v1/rides/ws/{ride_id}/passengers?token=JWT`** ומקבל עדכונים.
- **אימות WebSocket**: `get_current_user_ws` ב־`app/api/dependencies/auth.py` — טוקן מ־query string, מאמת JWT, מחזיר `WsUser` או `None` (**ללא DB** בזמן connect).

### פרונט (ביצועים ו-UX)

קוד: [`frontend/src/hooks/useLocationBroadcast.ts`](../../frontend/src/hooks/useLocationBroadcast.ts), [`usePassengerLocationBroadcast.ts`](../../frontend/src/hooks/usePassengerLocationBroadcast.ts), [`useLocationWatcher.ts`](../../frontend/src/hooks/useLocationWatcher.ts), [`useDriverLocation.ts`](../../frontend/src/hooks/useDriverLocation.ts), [`usePassengerLocations.ts`](../../frontend/src/hooks/usePassengerLocations.ts), [`useMapMarker.ts`](../../frontend/src/hooks/useMapMarker.ts); מסכים: [`LiveMapModal`](../../frontend/src/components/LiveMapModal/index.tsx), [`LiveRideMapModal`](../../frontend/src/components/LiveRideMapModal/index.tsx).

- **שידור לשרת (POST)**: `watchPosition` + **throttle ~1.5s** (`throttleMs: 1500`) לפני `postDriverBookingLocation` / `postPassengerBookingLocation` — איזון בין רענון למספר בקשות.
- **גאולוקציה**: בשידור — `maximumAge: 0` (מיקום טרי יחסית); במודלי מפה חיה (`LiveMapModal` / `LiveRideMapModal`) לציור “אני” על המפה — `maximumAge: 1000` (פשרה מול סוללה).
- **סמני Google Maps**: `useMapMarker` יוצר `Marker` **פעם אחת** לפי `map` + אופציות, ומעדכן רק `setPosition` / `setVisible` כשהמיקום משתנה — בלי למחוק וליצור marker בכל עדכון (מונע ריצוד ועלות מיותרת).

---

סיכום “להצגה”: [`../ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md).
