# LinkUp — Feature Decisions (Why / Alternatives / Trade-offs)

מסמך **מקביל** ל-[ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md).  
**HIGHLIGHTS** = "מה בניתי + איפה בקוד". **מסמך זה** = להצגה בראיון: בעיה, החלטה, חלופות, מחיר, משפט פתיחה קצר.

> פירוט ADR מלא: [adr/ARCHITECTURE_DECISIONS_BACKEND.md](adr/ARCHITECTURE_DECISIONS_BACKEND.md) (§1–25) ו־[adr/ARCHITECTURE_DECISIONS_FRONTEND.md](adr/ARCHITECTURE_DECISIONS_FRONTEND.md), [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md).

---

<a id="outbox"></a>

## Outbox + RabbitMQ

| | |
|--|--|
| **בעיה** | אחרי `commit` ב-DB רוצים לאירוע חיצוני (מייל, FCM) — `publish` ישיר אחרי commit או אם הברוקר/שרת נופלים = אובדן או כפילות. |
| **החלטה** | שורה ב-`outbox_events` **באותה טרנזקציה** עם שינוי עסקי; worker מפרסם ליעדי dispatch (RabbitMQ / Redis לפי `targets`) עם **LISTEN/NOTIFY** על חיבור Postgres ישיר (`DATABASE_URL_DIRECT`, לא PgBouncer) + מנגנון fallback polling. |
| **אלטרנטיבות** | (1) Publish ישיר — פשוט אבל fragile. (2) Kafka — כבד יותר לסקייל נוכחי. (3) SQS — vendor lock, דורש מודל mental שונה. |
| **יתרון** | **at-least-once** + עקביות DB/אירוע; ה-API לא מחכה ל-latency של הברוקר. |
| **Trade-off** | צריך idempotency בצרכנים; מורכבות תפעול (worker + monitoring). |
| **Interview pitch (≈30s)** | *"יישמתי outbox: האירוע נשמר בטרנזקציה יחד עם הדאטה, אז אם הפרוסס קורס או Rabbit זמנית למטה — לא מאבדים. Worker מפרסם ל-Rabbit. המחיר הוא at-least-once אז בצרכנים בודקים idempotency."* |
| **הפניה** | ADR §4, HIGHLIGHTS §6, [architecture/EVENTS.md](architecture/EVENTS.md) |

---

<a id="outbox-skip-locked"></a>

## Outbox — `FOR UPDATE SKIP LOCKED` (מקביליות workers)

| | |
|--|--|
| **בעיה** | הרצת **יותר ממופע אחד** של `notification-worker` (או ריצות מקביליות על אותו DB) עלולה לגרום לשני workers “להתחרות” על אותה שורת `outbox_events` ב-**`SELECT ... FOR UPDATE`** — נעילות ארוכות / המתנה. |
| **החלטה** | `OutboxRepository.get_pending_events` בוחר שורות **PENDING** עם **`with_for_update(skip_locked=True)`** — worker שנתקל בשורה שכבר נעולה על ידי גורם אחר **מדלג** ל-row הבא בלי לחסום. |
| **אלטרנטיבות** | (1) Worker יחיד — פשוט אבל אין scale-out אופקי. (2) משיכה ללא נעילה — סיכון double-process על אירוע זהה. |
| **יתרון** | מאפשר **scale-out** של outbox publishers בזמן שמתקן **ordering per batch** בסדר `created_at` + `LIMIT`. |
| **Trade-off** | עדיין **at-least-once** ברמת Rabbit; צרכנים חייבים **idempotency** (כבר דרישה בדפוס Outbox). |
| **Interview pitch (≈20s)** | *"במסלול Outbox הוספתי **SKIP LOCKED** כדי שכמה workers יוכלו למשוך batches במקביל בלי להיתקע אחד על השני על אותה שורה."* |
| **הפניה** | [`backend/app/infrastructure/outbox/repository.py`](../backend/app/infrastructure/outbox/repository.py), ADR §4, [architecture/EVENTS.md](architecture/EVENTS.md) |

---

<a id="s3-delete-objects-avatar-async"></a>

## S3 — מחיקת prefix ב-`DeleteObjects` + הסרת אווטאר אסינכרונית

| | |
|--|--|
| **בעיה** | Listing של כל המפתחות ל־RAM + **`delete_object` פר פריט** מגדילים משך קריאה, מספר round-trips וסיכון timeout; הסרת אווטאר סינכרונית מה-HTTP מחברת latency משתמש לנפח אובייקטים בתיק המשתמש. |
| **החלטה** | (1) **זרימה**: `iter_prefix_keys` → צבירת מפתחות עד 1000 → **`delete_objects`** עם טיפול ב־`Errors`. (2) **`remove_avatar`**: איפוס `users.avatar_*` + **`publish_to_outbox(..., "user.avatar_remove")`** באותה טרנזקציה; מחיקת `avatars/{user_id}/` ב־[`avatar_tasks`](../backend/app/workers/tasks/avatar_tasks.py). |
| **אלטרנטיבות** | מחיקה סדרתית (פשוט, גרוע בסקייל); S3 Lifecycle בלבד (לא מסונכן מייד עם שינוי מצב DB); משימת Celery חיצונית בלי Outbox — פחות עקביות מול טרנזקציה. |
| **יתרון** | פחות זיכרון וקריאות API; פרופיל משתמש חוזר מהר; אותה מודל **DB + אירוע** כמו העלאת אווטאר. |
| **Trade-off** | חלון קצר שבו DB ללא תמונה אבל קבצים עדיין ב-S3 אם worker מאחר; מתקבל בהחלפת אווטאר/מחיקה רכה בשירותים מבוזרים. |
| **הפניה** | [`backend/app/infrastructure/s3/client.py`](../backend/app/infrastructure/s3/client.py), [`service.py`](../backend/app/infrastructure/s3/service.py), [`backend/app/domain/users/service.py`](../backend/app/domain/users/service.py), [STORAGE.md](architecture/STORAGE.md), [EVENTS.md](architecture/EVENTS.md) |

---

<a id="rabbitmq-pr1-pr2"></a>

## RabbitMQ reliability refactor (PR1 + PR2)

| | |
|--|--|
| **בעיה** | consumer loop בודד + channel משותף לכל flows יצרו סיכון ל-crash loops שקטים ול-backpressure בין consume/publish. |
| **החלטה** | PR1: supervision עם draining states ו-`max_retries` ל-loopים ארוכי חיים. PR2: הפרדת clients לפי תפקיד (`rabbit_client`, `outbox_rabbit_client`, `worker_rabbit_client`) + channel isolation לכל queue + `QueueSpec` מרכזי לטופולוגיה. |
| **אלטרנטיבות** | (1) להשאיר singleton channel ולתקן נקודתית חריגות. (2) חיבור נפרד לכל worker/task — אמין אבל כבד מדי ל-`t3.medium`. |
| **יתרון** | בידוד עומסים בין publish/consume, recovery יותר צפוי, ויכולת לנהל policy ברמת queue ממקור אמת אחד. |
| **Trade-off** | יותר שכבת infra וקונפיגורציה; דורש משמעת תיעוד כדי לשמור sync בין topology לקוד worker. |
| **Interview pitch (≈30s)** | *"ב-PR1 הוספתי supervision ודראינינג כדי למנוע task death שקט. ב-PR2 פיצלתי נתיבי RabbitMQ לפי תפקידים והעברתי queue policies ל-QueueSpec מרכזי. כך צמצמתי coupling בין consumers ו-publishers בלי להוסיף תשתית ענן חדשה."* |
| **הפניה** | `backend/app/infrastructure/rabbitmq/{client.py,consumer.py,supervisor.py,topology.py}`, `architecture/EVENTS.md`, `ENGINEERING_HIGHLIGHTS.md` |

---

<a id="rabbitmq-graceful-drain"></a>

## RabbitMQ consumer — graceful shutdown (drain in-flight)

| | |
|--|--|
| **בעיה** | SIGTERM / עצירת worker בזמן עיבוד הודעה עלולה לגרום ל-**אובדן** עבודה או ל-**requeue** לא עקבי אם לא מחכים לסיום tasks. |
| **החלטה** | `ConsumerSupervisor` עוקב אחרי `asyncio.Task` של handler; ב-**draining** מפסיקים לקבל deliveries חדשים, מחכים עד **`drain_timeout_seconds`** (ברירת מחדל **30s**) לסיום inflight; אם נשארו — **cancel** + המתנה קצרה. |
| **יתרון** | כיבוי של worker בפריסה / `docker compose stop` פחות מסוכן לכפילויות/איבוד ביניים. |
| **הפניה** | [`backend/app/infrastructure/rabbitmq/consumer.py`](../../backend/app/infrastructure/rabbitmq/consumer.py) (`ConsumerSupervisor`, `ConsumerState`) |

---

<a id="auth-session-teardown"></a>

## Frontend — איחוד teardown לסיסמה / פג refresh / bootstrap נכשל

| | |
|--|--|
| **בעיה** | מספר מסלולי ניקוי בפרונט (**logout**, **`refreshUser`** catch, bootstrap **`fetchCurrentUser`** catch, ו-**`refreshAccessToken`** ב-`client.ts`) שיכפלו לוגיקה; כשזרימת הרענון נכשלת ב-axios, הקוד הקודם השאיר טוקן ב-React context כ‑**authenticated** בזמן ש-**localStorage** כבר התרוקן → משתמש "תקוע" על רוט מוגן. |
| **החלטה** | פונקציה אחת **`tearDownSession({ reason })`** ב־[`AuthContext.tsx`](../frontend/src/context/AuthContext.tsx): **`user-action`** — `patchFcmToken(null)`, `logoutSession()` (שגם מנקה refresh cookie בשרת), אחר כך תמיד `cleanupFCM()`, `queryClient.clear()`, **`Sentry.setUser(null)`** (PROD), `clearTokens`, `isAuthenticated=false`. **`session-expired`** / **`bootstrap-failed`** מדלגים על קריאות HTTP (JWT לא מהימן), אבל מריצים את אותו **local teardown**. **`client.ts`**: **`refreshAccessToken`** שולח `POST /auth/refresh` עם `withCredentials: true` (ה-refresh token נשלח כ-HttpOnly cookie אוטומטית — **H19**); בעת catch — **`clearTokens()`** ואז **`window.dispatchEvent('auth:session-expired')`** עם **guard רק-entry** למניעת N אירועים מקבילים; בסוף זרימת 401 לאחר כשל refresh — סימון **`__sentryCaptured`** לפני `reject`. |
| **Sentry noise** | ב־[`queryClient.ts`](../frontend/src/api/queryClient.ts), **`captureExceptionOnce`** מדלג על **401** בלבד (לא **403** — RBAC צריך להישאר visible). |
| **Trade-off** | בלי **`patchFcmToken(null)`** בנתיב **session-expired** (מתכוון — מונע רקורסיה 401 והטוקן ב-DB יתעדכן ב-Re-login כשFirebase מחזיר token); משתמש אחר מאותה דפדפן עם אותו install — תלוי בהתנהגות Firebase ובניקוי NotRegistered בעתיד ב-backend אם צריך. |
| **Interview pitch (≈30s)** | *"מרכזתי teardown לסוג הודעות: logout מפורש מול הרחבת session שמתה. Axios לא משתלב בצורה הגיונית בתוך React — CustomEvent מתנתק, guard מונע storm, והמסך עובר ל-login כי ProtectedRoute רואה isAuthenticated=false."* |
| **הפניה** | Frontend ADR §21, [`client.ts`](../frontend/src/api/client.ts), [`queryClient.ts`](../frontend/src/api/queryClient.ts), [`AuthContext.tsx`](../frontend/src/context/AuthContext.tsx) |

---

<a id="refresh-token-httponly-cookie"></a>

## H19 — Refresh token ב-HttpOnly cookie (XSS mitigation)

| | |
|--|--|
| **בעיה** | Refresh token ב-`localStorage` חשוף לכל XSS — תוקף שמזריק סקריפט יכול לגנוב את ה-token ולחדש sessions ללא הגבלה. |
| **החלטה** | הועבר ל-**`Set-Cookie: linkup_refresh_token`** עם **`HttpOnly; Secure; SameSite=lax; Path=/api/v1/auth`**. Backend: helper functions `_set_refresh_cookie` / `_clear_refresh_cookie` ב-`auth/router.py`; ה-token לא חוזר ב-JSON (הוסר מ-`LoginResponse` / `RefreshResponse`). Frontend: axios `withCredentials: true`; `setTokens(access)` ללא refresh; `clearTokens()` מוחק legacy key מ-localStorage (one-time migration). |
| **CSRF** | `SameSite=lax` חוסם cross-origin POST (browser default); path scope (`/api/v1/auth`) מונע שליחת cookie לנתיבים אחרים; כל ה-endpoints הרלוונטיים הם POST-only. אין GET שמשנה state. לכן — אין צורך ב-CSRF token נפרד. |
| **Secure flag** | נגזר מ-`settings.FORCE_HTTPS_REDIRECT` — `True` בפרודקשן (מאחורי nginx TLS), `False` בפיתוח מקומי (localhost HTTP). |
| **Migration (frontend)** | `clearTokens()` כולל `localStorage.removeItem('linkup_refresh_token')` — מנקה key ישן אצל משתמשים קיימים שעדיין מחזיקים ערך מהגרסה הקודמת. |
| **Trade-off** | cookie לא נגיש מ-JS — אי אפשר "לבדוק" refresh token בצד לקוח; הדפדפן שולח אוטומטית. הגנת CSRF ב-SameSite=lax מספיקה לאתרים שלא משתמשים ב-GET לפעולות שמשנות state (לינקאפ לא). |
| **הפניה** | [`backend/app/domain/auth/router.py`](../backend/app/domain/auth/router.py), [`frontend/src/api/client.ts`](../frontend/src/api/client.ts), `docs/ENGINEERING_HIGHLIGHTS.md` |

---

<a id="chat-ws"></a>

## Real-time chat + chat-ws (Go)

| | |
|--|--|
| **בעיה** | הודעות 1:1 + typing + presence — צריך הרבה idle connections; לא רוצים לייבל את path ה-DB ב-Python. |
| **החלטה** | **Go `chat-ws`**: WebSocket, JWT ב-handshake, מנוי ל-**Redis** (`chat:conversation:*`, notification/typing, `user:*:events`), fan-out. Python שומר הודעה + publish ל-Redis. במסלול הנכנס: **`SetReadLimit(2048)`** על המסר; דילול **פרסום `typing_*` לרדיס** פר־חיבור עם **`x/time/rate`** (**`ping`** פטור). **מסגרות WS יוצאות** יכולות לאחות כמה JSONים עם newline — הפרונט מפצל לפני parse (**`useUserEventStream`**); **`message_read`** דורש **`recipient_id`** ב-payload כדי לנתב עדכוני read receipt חיים לשולח. |
| **אלטרנטיבות** | (1) WebSocket ב-FastAPI בלבד — אפשרי אבל per-connection cost גבוה ב-Python. (2) SaaS (Pusher/Ably) — עלות+vendor. (3) רק long polling — גרוע ל-UX. |
| **יתרון** | הפרדת "מסע real-time" משכבת REST/DB; גורוטינים זולים per connection. |
| **Trade-off** | שני runtimes (Python + Go); אותו `SECRET_KEY` ל-WS. |
| **Interview pitch (≈30s)** | *"צ'אט: FastAPI שומר ב-Postgres ומפרסם ל-Redis, chat-ws ב-Go מנוי ודוחף ללקוח. בחרתי Go כי אלפי חיבורים idle זולים שם ולא שולפים load על SQLAlchemy."* |
| **הפניה** | [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md) (כולל §7–§8), HIGHLIGHTS §4 + Latest updates, [architecture/REALTIME.md](architecture/REALTIME.md), [chat-ws/README.md](../chat-ws/README.md) |

---

<a id="chat-ws-operational-hardening"></a>

## chat-ws operational hardening (H7–H10)

| | |
|--|--|
| **בעיה** | (H7) `docker-compose.yml` healthcheck references `/healthz` but no handler existed — always 404; combined with subscriber death, chat-ws appears alive but delivers zero messages. (H8) raw `http.ListenAndServe` without `Shutdown` — SIGTERM instantly kills active WS connections. (H9) no `SetReadDeadline`/`SetPongHandler` — dead clients leak goroutines forever. (H10) zero `recover()` — any goroutine panic crashes the entire process. |
| **החלטה** | **H7:** `/healthz` checks Redis PING **and** `Hub.SubscribersHealthy()` — three `atomic.Int64` timestamps (chat/offline/online) updated on each successful `(P)Subscribe`, with 2-min staleness threshold; seeded to `now` in `NewHub` for startup grace. **H8:** `*http.Server` + `srv.Shutdown(shutdownCtx)` with 10s timeout. **H9:** `conn.SetReadDeadline(pongWait)` + `SetPongHandler` before read loop. **H10:** shared `internal/safego/safego.go` with `RecoverPanic(component, op)` — `defer` in every independent goroutine. |
| **אלטרנטיבות** | (H7) Redis PING only — doesn't catch dead subscribers. (H10) inline `recover()` per function — code duplication across `hub`/`redis` packages. |
| **יתרון** | Healthcheck catches real failure mode (alive but deaf); deploy drains gracefully; dead clients detected in ≤60s; single goroutine crash doesn't take down process. |
| **Trade-off** | H7 subscriber liveness tracks subscription success, not message receipt — legitimate silence doesn't trigger staleness (acceptable: if subscriber disconnects, `runOnce` returns and timestamp goes stale). H10 recovery swallows the panic — the goroutine stops silently (logged with full stack trace). |
| **Interview pitch (≈35s)** | *"הוספתי healthz שבודק לא רק Redis PING אלא גם שכל subscriber goroutine באמת subscribed — עם atomic timestamps ו-2-minute threshold. Graceful shutdown, read deadline לזיהוי לקוחות מתים, ו-panic recovery שמשותף ב-internal/safego כדי שקריסה של goroutine אחת לא תפיל את כל התהליך."* |
| **הפניה** | ADR chat-ws §8, [architecture/REALTIME.md](architecture/REALTIME.md), [`chat-ws/cmd/server/main.go`](../chat-ws/cmd/server/main.go), [`chat-ws/internal/hub/hub.go`](../chat-ws/internal/hub/hub.go), [`chat-ws/internal/safego/safego.go`](../chat-ws/internal/safego/safego.go) |

---

<a id="chat-thread-reconnect"></a>

## Chat thread — REST backfill על `WS onOpen` (`after`)

| | |
|--|--|
| **בעיה** | אם **`lastMessageIdRef`** היה **`null`** (שיחה בלי עדיין הודעות ב־state, או באג **`maxId \|\| null`**), הקוד הקודם **לא קרא** **`fetchMissedMessages`** בעליית החיבור — פער בשיחות בזמן ניתוק. בשלב מאוחר יותר: גם קריאה **בודדת** עם **`after`** ו־**`limit` 30** השאירה **זנב** שקט בהפסקות ארוכות (יותר מ־30 הודעות בפער). |
| **החלטה** | **`onopen` תמיד** — **`fetchMissedMessages(lastMessageIdRef ?? 0)`**; עדכון ref — **`messages.length > 0 ? max(message_id) : null`**. ההשלמה בפועל עוברת דרך **`fetchMissedGap`** — עמוד ראשון עם **`after`**, המשך עם **`before=next_cursor`** כל עוד **`has_more`**, בהתאם לחוזה ב־[API messages](architecture/API.md) (זהה ל־pagination של גלילה לעבר הישן). |
| **Trade-off** | הרבה יותר HTTP בפערים גדולים (עד **~50** עמודים × **`limit` 30**, עם **שני** ניסיונות חוזרים לכל עמוד); כפילויות נסגרות ע"י **`message_id`** ב־merge; אם הגענו למכסה או השיחה מתחלפת באמצע — חלק מהפער עלול להישאר (**`shouldAbort`** / **`cidRef`**). |
| **הפניה** | [architecture/REALTIME.md](architecture/REALTIME.md), [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md) (Latest updates), [`fetchMissedGap.ts`](../frontend/src/pages/MessageThread/fetchMissedGap.ts), [`fetchMissedGap.test.ts`](../frontend/src/pages/MessageThread/fetchMissedGap.test.ts), [`useChatWebSocket.ts`](../frontend/src/pages/MessageThread/useChatWebSocket.ts), [`useConversationMessages.ts`](../frontend/src/pages/MessageThread/useConversationMessages.ts) |

---

<a id="frontend-ws-reconnect-backoff"></a>

## Frontend — WebSocket reconnect delay (backoff + jitter)

| | |
|--|--|
| **בעיה** | עיכוב **קבוע** (~3s) בין ניסיונות חיבור מחדש ל־WebSocket **מסנכרן** לקוחות אחרי נפילה המונית (deploy, restart, blip) — **thundering herd** על chat-ws / backend / Nginx בעת התאוששות. |
| **החלטה** | פונקציה טהורה **`computeReconnectDelayMs`** ב־[`reconnectBackoff.ts`](../frontend/src/utils/reconnectBackoff.ts): בסיס **3s**, **כפול** בכל כשל, תקרה **30s**, **±20% jitter** על הערך אחרי התקרה; מונה ניסיונות **מתאפס ב־`onopen`** ובהרצת effect חדשה כשמשנים **`cid`** / **`reconnectKey`**. מחובר ל־[`useChatWebSocket.ts`](../frontend/src/pages/MessageThread/useChatWebSocket.ts), [`useUserEventStream.ts`](../frontend/src/hooks/useUserEventStream.ts) (עוטף [`useReconnectingWebSocket.ts`](../frontend/src/hooks/useReconnectingWebSocket.ts) לערוץ **`user:{id}:events`**), [`useRideWebSocket.ts`](../frontend/src/hooks/useRideWebSocket.ts), [`useReconnectingWebSocketState.ts`](../frontend/src/hooks/useReconnectingWebSocketState.ts); **`reconnectDelayMs`** בשני ההוקים הכלליים משמש **baseMs** כברירת מחדל (**3000**). |
| **Trade-off** | זמן עד התאוששות מלאה עלול להתארך אחרי שרידור ארוך של כשלים; לעומת זאת פחות עומס הקצפתי והתנהגות נדיבה יותר לשרת. |
| **Interview pitch (≈30s)** | *"אותה תפיסה כמו Redis backoff בבקאנד — רק שגם ה-clients לא מציפים את השרת ברגע שהשירות חוזר: exponential backoff, cap 30s, jitter, ומונה שמתאפס ב-onopen. **`computeReconnectDelayMs` אחד** משותף לצ’אט, לאירועי `user:*` על chat-ws, ל-WS נסיעות ב-FastAPI ול-GPS."* |
| **הפניה** | [architecture/REALTIME.md](architecture/REALTIME.md), [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md), [`reconnectBackoff.test.ts`](../frontend/src/utils/reconnectBackoff.test.ts) |

---

<a id="frontend-ws-token-freshness"></a>

## Frontend — WebSocket token freshness gate + visibility-aware reconnect

| | |
|--|--|
| **בעיה** | Access token (TTL 30 דקות) מועבר כ-`?token=` ב-WebSocket URL. כשלשונית הדפדפן ברקע, Chrome/Edge מצמצמים timers; ה-pong לא מגיע בזמן (60s deadline בצד Go) → השרת סוגר חיבור. בניתוק, ה-reconnect loop קורא token מ-`localStorage` — אך שום בקשת HTTP לא נשלחה בזמן ה-idle ולכן ה-Axios interceptor לא רענן אותו. התוצאה: לולאת reconnect אינסופית עם token פג תוקף. |
| **החלטה** | (1) **`ensureFreshToken()`** ב-[`tokenRefresh.ts`](../frontend/src/api/tokenRefresh.ts) — gateway משותף ל-Axios interceptor ול-WS hooks: פענוח `exp` מ-JWT ללא crypto (`atob`); אם < 60s לתפוגה → `POST /auth/refresh` (HttpOnly cookie) עם coordinated single-flight (אותו `isRefreshing` queue שמטפל בכמה callers במקביל). (2) **`visibilitychange`** listener בכל hook: כשלשונית חוזרת לפוקוס ואין WS פתוח → reconnect מיידי (attempt=0) דרך `ensureFreshToken`. (3) **`isTokenExpiredOrNearExpiry`** ב-[`tokenUtils.ts`](../frontend/src/utils/tokenUtils.ts) — פונקציה טהורה שמפענחת payload בלבד (base64). |
| **Trade-off** | ייתכן refresh HTTP מיותר כשהטוקן קרוב ל-60s אבל עדיין תקף; לעומת זאת — WS reconnect לעולם לא יישלח עם token שפג. |
| **Interview pitch (≈30s)** | *"Access token פג אחרי 30 דקות, אבל ה-WS hook קרא אותו מ-localStorage בלי לבדוק exp. הוספתי שער freshness ששותף גם עם Axios interceptor — אם JWT < 60s לתפוגה, refresh חד-פעמי מרוכז רץ לפני כל ניסיון חיבור. בנוסף, visibilitychange listener מזהה חזרה מרקע ומפעיל reconnect מיידי עם token טרי."* |
| **הפניה** | [architecture/REALTIME.md](architecture/REALTIME.md), [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md), [`tokenRefresh.ts`](../frontend/src/api/tokenRefresh.ts), [`tokenUtils.ts`](../frontend/src/utils/tokenUtils.ts), [`useReconnectingWebSocket.ts`](../frontend/src/hooks/useReconnectingWebSocket.ts), [`useChatWebSocket.ts`](../frontend/src/pages/MessageThread/useChatWebSocket.ts) |

---

<a id="chat-optimistic-outbound"></a>

## Chat — optimistic outbound UI (frontend)

| | |
|--|--|
| **בעיה** | משתמש לוחץ Send ומחכה ל-REST — תחושת המתנה גם כשהרשת איטית; צריך גם ליישר עם WS שיכול להגיע לפני או אחרי תשובת השרת בלי כפילויות בבועות. |
| **החלטה** | רשימת הודעות ב-UI היא **`ChatListRow[]`**: **`confirmed`** (עוטף **`MessageResponse`**) או **`pending`** עם **`client_message_id`** (UUID). בשליחה: append **pending**, ניקוי שדה הקלט; ב-success REST או פריים WS — **`applyInboundRealMessage`** מסיר את ה-pending המתואם ומזין **`appendMessageDedupById`**; בכשל REST — **`removePendingByClientId`** והחזרת טקסט. **`useMessageThread`**: **`outboundPendingRef`** + **`processChatWebSocketMessage`**; **`useChatPopup`**: אותו מיזוג ללא WS. מפתח אידמפוטנטיות: **`consumeOrCreateKey` / `resetOutboundKey`** ללא שינוי. |
| **Trade-off** | שליחה בודדת בכל רגע (`sending`) — לא תור multi-flight; מודל pending לא נשמר ב-API (רק ב-state). |
| **הפניה** | [`types/chatList.ts`](../frontend/src/types/chatList.ts), [`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts), [`useMessageThread.ts`](../frontend/src/pages/MessageThread/useMessageThread.ts), [`useChatPopup.ts`](../frontend/src/components/ChatPopup/useChatPopup.ts), **ADR Frontend §2**, [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md) (Latest updates) |

---

<a id="chat-plaintext"></a>

## Chat: plaintext + דחיית HTML (XSS)

| | |
|--|--|
| **בעיה** | הודעות נשמרות ב-`messages.body`; אפשר לייצר **stored** payload (HTML) שישפיע עתידית על render או ייצוא. |
| **החלטה** | `MessageCreate` (Pydantic) — **דחייה** אם מזוהה תבנית תג HTML (`<...>`); הודעת שגיאה ברורה. מדיניות מוצר: **צ'אט = טקסט בלבד**. |
| **אלטרנטיבות** | (1) DOMPurify/escape בצד הלקוח בלבד — לא מספיק ל-API אחר. (2) Strip שקט — משנה תוכן בלי שקיפות. |
| **יתרון** | הכנסה "נקייה" ל-DB; עקבי לכל consumer (UI, אדמין עתידי, ייצוא). |
| **Trade-off** | טקסט לגיטימי עם `<`/`>` עלול להידחות; זו החלטת product. |
| **Interview pitch (≈30s)** | *"רינדור הודעה ב-React כבר בטוח כטקסט, אבל חיזקתי בשרת: הודעות שממלאות pattern של תג HTML נדחות, כי זה contract של plain text. זה שכבה נגד stored XSS, לא רק ref reflected."* |
| **הפניה** | ADR **§22**, [backend/app/domain/chat/schema.py](../backend/app/domain/chat/schema.py) |

---

<a id="chat-rate-limit"></a>

## Chat rate limit (per-user)

| | |
|--|--|
| **בעיה** | ספאם הודעות בצ'אט יוצר עומס כתיבה, רעש למשתמש השני וסיכון להתנהגות abuse. |
| **החלטה** | Dependency ייעודי `rate_limit_chat` בשכבת API: מפתח Redis פר-משתמש `ratelimit:chat:{user_id}`, חלון 60 שניות, מקסימום 30 הודעות לדקה ל-endpoint `POST /chat/conversations/{conversation_id}/messages`. |
| **אלטרנטיבות** | (1) Rate limit לפי IP בלבד — לא מדויק למשתמשים מאחורי NAT. (2) מנגנון throttling רק בפרונט — קל לעקיפה. (3) Queue עם slow mode — מורכב לדרישה הנוכחית. |
| **יתרון** | הגבלה הוגנת ברמת משתמש אותנטי, אטומיות מלאה ב-Lua, ללא שינוי בדומיין הצ'אט. |
| **Trade-off** | Redis למטה => fail-open לצורך זמינות (הגנה זמנית נחלשת). |
| **Interview pitch (≈30s)** | *"הוספתי rate limit פר-משתמש לשליחת הודעות בצ'אט, 30 לדקה, באלגוריתם Token Bucket אטומי דרך Lua script. fail-open אם Redis נופל כדי לא לשבור את הצ'אט."* |
| **הפניה** | [../backend/app/api/dependencies/rate_limit.py](../backend/app/api/dependencies/rate_limit.py), [../backend/app/domain/chat/router.py](../backend/app/domain/chat/router.py), [../ARCHITECTURE.md](../ARCHITECTURE.md), [#rate-limit-token-bucket](#rate-limit-token-bucket) |

---

<a id="rides-rate-limit"></a>

## Ride creation rate limit (per-user)

| | |
|--|--|
| **בעיה** | משתמש זדוני או באג בקליינט יכולים ליצור עשרות/מאות נסיעות בדקות — עומס DB, רעש בחיפוש נוסעים, ושריפת משאבי geocoding/routing. |
| **החלטה** | Dependency `rate_limit_rides` בשכבת API: מפתח Redis פר-משתמש `ratelimit:rides:{user_id}`, **Sliding Window** (אותו Lua כמו auth), מקסימום **10 נסיעות לשעה**. מוחל על `POST /rides/` (יצירה) ו-`POST /rides/preview-routes` (preview — כי מפעיל Google Maps). |
| **אלטרנטיבות** | (1) Token Bucket — מאפשר burst של 10 נסיעות ברצף, שלא מתאים ליצירת נסיעות (לא UX burst). (2) Rate limit על preview בלבד — לא חוסם יצירות abuse. (3) Rate limit משותף עם auth (IP) — לא מדויק, ולא שייך לאותו threat model. |
| **יתרון** | אלגוריתם Sliding Window מונע burst abuse; per-user key ולא per-IP — הגנה מדויקת גם מאחורי NAT; אותה תשתית Lua/Redis כמו auth ו-chat. |
| **Trade-off** | preview ו-create חולקים אותו counter — 10 previews יחסמו create באותה שעה; זה מודע — preview מפעיל Google Maps API ולכן גם הוא משאב מוגבל. Redis למטה → fail-open. |
| **Interview pitch (≈25s)** | *"הגבלתי יצירת נסיעות ל-10 לשעה פר משתמש עם Sliding Window — אותו Lua כמו auth, אבל כאן per-user ולא per-IP. גם preview נכנס לאותו counter כי הוא מפעיל Google Maps."* |
| **הפניה** | [`../backend/app/api/dependencies/rate_limit.py`](../backend/app/api/dependencies/rate_limit.py), [`../backend/app/domain/rides/router.py`](../backend/app/domain/rides/router.py), [`../backend/app/core/config.py`](../backend/app/core/config.py) (`RATE_LIMIT_RIDES_*`), [#rate-limit-token-bucket](#rate-limit-token-bucket) |

---

<a id="sentry"></a>

## Sentry — error monitoring (production)

| | |
|--|--|
| **בעיה** | שגיאות production אינן גלויות בזמן אמת — אי אפשר לאתר רגרסיות חדשות בלי לחפש ידנית בלוגים. |
| **החלטה** | Sentry SDK — backend: `sentry_sdk.init()` בתוך `setup_logging()` כש-`SENTRY_DSN` מוגדר (FastAPI/SQLAlchemy/Redis integrations, `traces_sample_rate=0.1`); `capture_exception` ל-5xx בלבד ב-`link_up_exception_handler`. Frontend: `Sentry.init()` ב-`main.tsx` (guard: `PROD + VITE_SENTRY_DSN`); `captureException` ב-axios interceptor (5xx), `ChatErrorBoundary`, `RouteErrorBoundary`. |
| **אלטרנטיבות** | (1) Rollbar / Datadog — אותו עיקרון, עלות גבוהה יותר. (2) Prometheus + Grafana — מדדים בלבד, אין stack traces. (3) לוגים בלבד — קשה לאתר רגרסיות בזמן אמת. |
| **יתרון** | stack traces מלאים עם `trace_id`; DSN לא נכנס ל-git (`.env` בלבד); fail-safe — אם Sentry down, השרת ממשיך. |
| **Trade-off** | capture ל-5xx בלבד מפחית רעש אבל עלול להחמיץ שגיאות לוגיקה שנבלעות או 4xx חריגים שתרצה לנטר בהמשך. |
| **Interview pitch (≈30s)** | *"הפעלתי Sentry: backend init ב-`logging.py` עם guard על `SENTRY_DSN`, capture רק ל-5xx כדי להפחית רעש. פרונט: init ב-`main.tsx` + שני error boundaries. DSN ב-`.env` בלבד — לא עולה ל-git."* |
| **הפניה** | [`../backend/app/core/logging.py`](../backend/app/core/logging.py), [`../backend/app/core/exceptions/handlers.py`](../backend/app/core/exceptions/handlers.py), [`../frontend/src/main.tsx`](../frontend/src/main.tsx) |

---

<a id="api-errors-linkuperror"></a>

## שגיאות API אחידות (`LinkUpError`, `error_code`, `trace_id`)

| | |
|--|--|
| **בעיה** | `HTTPException` עם `detail` שרירותי מקשה על לקוחות, i18n ו-Sentry — אין חוזה יציב לשדות שגיאה. |
| **החלטה** | תתי־מחלקות דומיין של **`LinkUpError`** + handlers גלובליים; בתגובה: `detail` עם **`error_code`**, **`message`**, **`trace_id`** (מיושר ל־**`X-Request-ID`** מה־middleware), ו־**`payload`** אופציונלי מסוגי; validation/DB/SQLAlchemy ממופים לפורמט אחיד. |
| **אלטרנטיבות** | (1) RFC 7807 בלבד בלי שכבת דומיין — פחות typed errors בקוד. (2) קודי שגיאה רק במספר HTTP — לא מספיק לפרונט ולניטור. |
| **יתרון** | לקוחות ופרונט יכולים להסתמך על **`error_code`**; לוגים ו-Sentry מתיישרים לאותו מזהה בקשה. |
| **Trade-off** | כל דומיין חדש צריך להשתמש ב־exceptions הטיפוסיים או לרשת מ־`LinkUpError` — דורש משמעת. |
| **Interview pitch (≈25s)** | *"הקשחתי חוזה אחיד: מחלקות שגיאה לפי דומיין, `trace_id` כמו request id, ו־handlers שמפים SQLAlchemy/validation לאותו JSON — הפרונט יודע מה לתרגם בלי לנחש טקסטים."* |
| **הפניה** | ADR §14, **[ERRORS.md](ERRORS.md)**, [`backend/app/core/exceptions/`](../backend/app/core/exceptions/), [`handlers.py`](../backend/app/core/exceptions/handlers.py) |

---

<a id="cursor-pagination"></a>

## Cursor pagination — נסיעות וצ’אט (לא offset עמוק)

| | |
|--|--|
| **בעיה** | `OFFSET` גדול על טבלאות שצומחות — שאילתה יקרה, ותוצאות "מדלגות" אם נכנסות רשומות חדשות בזמן גלילה. |
| **החלטה** | **נסיעות (חיפוש נוסע):** `after` + `limit` על מזהה cursor; **הודעות צ’אט (היסטוריה בשיחה):** `before` / `after` + `limit` לפי `message_id` — ראו [API messages](architecture/API.md); **אינבוקס רשימת שיחות:** `GET /chat/conversations` עם `limit` / `after` (cursor אטום) — [API inbox](architecture/API.md), פירוט: [#chat-inbox-cursor-pagination](#chat-inbox-cursor-pagination). |
| **אלטרנטיבות** | Keyset מורכב יותר לכל מסך; offset בלבד — פשוט אבל לא יציב ולא סקייל בצורה טובה. |
| **יתרון** | עומס סביר על DB בגלילה ארוכה; התאמה טבעית ל-“טען עוד” ול־reconnect (`after` אחרי WS). |
| **Interview pitch (≈15s)** | *"ברשימות שנשארות ארוכות עברנו ל-cursor על מזהים, לא offset — פחות full scan ופחーズ חיתוך באמצע עמוד."* |
| **הפניה** | ADR §10, [architecture/API.md](architecture/API.md) |

---

## Frontend data layer — TanStack React Query

| | |
|--|--|
| **בעיה** | קריאות רשת מפוזרות יוצרות policy לא עקבי ל-retry/cache ושגיאות כפולות ב-Sentry בין axios interceptors לבין שכבות UI. |
| **החלטה** | `QueryClient` מרכזי עם `QueryCache`/`MutationCache`, retry policy מוגדר (network/5xx בלבד), תמיכה ב-`Retry-After` (seconds/date), ו-`mutations.retry=false`. |
| **Dedup שגיאות** | axios מסמן `__sentryCaptured` לפני capture ל-5xx; React Query `onError` בודק marker ולא מדווח שוב. `ERR_CANCELED` מדולג בשתי השכבות. |
| **Query key convention** | factories typed (`qk`/`mk`) במקום keys ידניים מפוזרים, כולל `Record<string, unknown>` לפילטרים. |
| **יתרון** | cache/retry עקביים בכל הדומיינים, observability נקייה יותר (בלי double-capture), ובסיס טוב למיגרציה הדרגתית של מסכים ל-RQ hooks. |
| **Trade-off** | שכבת תשתית נוספת בפרונט ודורשת משמעת של key factories כדי למנוע drift. |
| **הפניה** | [`../frontend/src/api/queryClient.ts`](../frontend/src/api/queryClient.ts), [`../frontend/src/api/queryKeys.ts`](../frontend/src/api/queryKeys.ts), [`../frontend/src/api/client.ts`](../frontend/src/api/client.ts), ADR Frontend §13 |

---

## React Query migration Stage 3b — Groups + MyRides

| | |
|--|--|
| **בעיה** | `GroupContext` ו-`MyRides` ניהלו fetch/state ידני (`useState` + `useEffect`), כולל עדכוני WS ב-`setState`, מה שהקשה על עקביות cache ועל תחזוקה. |
| **החלטה** | להעביר `GroupContext` ל-`useQuery(qk.groups.list)` ולשמור את `useGroup()` contract זהה; להעביר `MyRides` ל-`useQuery(qk.rides.list)` + `useMutation(mk.rides.cancel)` עם invalidate על אירועי WS. |
| **מדיניות cache** | `GroupContext` משתמש ב-`staleTime=2m`; `MyRides` ב-`staleTime=30s`; `refreshGroups` ממומש דרך `queryClient.invalidateQueries`. |
| **עדכון בזמן אמת** | אירועי `RIDE_FINISHED/RIDE_CANCELLED/RIDE_ENDED/RIDE_STARTED` גורמים ל-invalidate של `qk.rides.list` במקום patch ידני מרובה. |
| **יתרון** | מקור אמת יחיד לרשימות קבוצות/נסיעות, פחות race conditions בצד לקוח, ומיגרציה בטוחה בלי שינוי UX או מבנה JSX/CSS. |
| **Trade-off** | דורש משמעת גבוהה לשימוש עקבי ב-query keys ומדיניות invalidation כדי למנוע stale data. |
| **הפניה** | [`../frontend/src/context/GroupContext.tsx`](../frontend/src/context/GroupContext.tsx), [`../frontend/src/pages/MyRides.tsx`](../frontend/src/pages/MyRides.tsx), [`../frontend/src/api/queryKeys.ts`](../frontend/src/api/queryKeys.ts) |

---

## OpenAPI snapshot code generation (Orval)

| | |
|--|--|
| **בעיה** | טייפים/clients ידניים בפרונט נוטים לסטייה מה-schema של backend עם הזמן. |
| **החלטה** | לייצר client/types אוטומטית מ-`frontend/openapi-snapshot.json` באמצעות Orval (`orval.config.ts`) ל-`frontend/src/api/generated`, עם mutator אחיד (`apiMutator`) שמתחבר ל-axios instance הקיים. |
| **Source of truth** | קבצי generated נכנסים ל-git במכוון כדי לשמור reviewable API contract snapshot בכל commit. |
| **אכיפה ב-CI** | `frontend-ci` מריץ gate ייעודי: `npm run gen:api` ואז `git diff --exit-code -- src/api/generated/` (אחרי `git update-index -q --refresh`) כדי לחסום merge כשיש drift. |
| **יתרון** | מפחית drift חוזי בין backend/frontend, מקטין boilerplate ידני, ומשפר type-safety בזמן קומפילציה. |
| **Trade-off** | דורש discipline תהליכי: כל שינוי schema מחייב regeneration לפני merge. |
| **הפניה** | [`../frontend/orval.config.ts`](../frontend/orval.config.ts), [`../frontend/src/api/client.ts`](../frontend/src/api/client.ts), [`../frontend/src/api/generated/client.ts`](../frontend/src/api/generated/client.ts) |

### Stage 2 — snapshot uncommitted, dedicated workflow

| | |
|--|--|
| **בעיה** | `frontend/openapi-snapshot.json` היה **תוצר ביניים מקומיט** ל-git שנערך ידנית בסקריפטי patch (`scripts/patch-openapi-manifest-passengers.py`) כשלא היה ניתן לייצא ישירות מ-FastAPI. כפילות מקור-אמת: הסכמה הייתה גם ב-`app.openapi()` וגם בקובץ JSON מקומיט שיכל לסטות בשקט. ה-job `contract-codegen` ב-`frontend-ci.yml` בדק drift רק על `src/api/generated/` ולא על ה-snapshot עצמו, כלומר schema של backend יכלה להשתנות בלי שאף בדיקה תיכשל עד שמישהו ירוץ patch + Orval. |
| **החלטה** | (1) ה-snapshot יורד מ-git: [`frontend/.gitignore`](../frontend/.gitignore) מסמן את `openapi-snapshot.json` כתוצר build. (2) Workflow ייעודי [`.github/workflows/openapi-contract.yml`](../.github/workflows/openapi-contract.yml) מייצא טרי בכל ריצה: `uv sync` → [`backend/scripts/export_openapi.py`](../backend/scripts/export_openapi.py) → `npm run gen:api` → `git diff --exit-code -- frontend/src/api/generated/`. (3) ה-job `contract-codegen` הוסר מ-[`frontend-ci.yml`](../.github/workflows/frontend-ci.yml). (4) DX מקומי: target `openapi` ב-[`Makefile`](../Makefile) השורש + `npm run openapi:sync` ב-[`frontend/package.json`](../frontend/package.json) שמפנה אליו. (5) `scripts/patch-openapi-manifest-passengers.py` נמחק. |
| **למה לא DB ב-CI** | `app.openapi()` הוא קריאה lazy: `setup_admin(app, engine)` מסתפק ב-engine (לא מתחבר עד request), Firebase init מטפל ב-credentials חסרים עם warning בלבד, ו-lifespan לא רץ בלי uvicorn. כתוצאה — ה-workflow רץ ללא service Postgres, בלי env vars מיוחדים, ב-< 30 שניות. |
| **Trade-off** | מפתח ש-`from app.main import app` לא מצליח אצלו לוקלית (למשל בעיית DLL ב-Windows) חייב להסתמך על ה-CI לאמת את הסכמה — אבל ה-CI ממילא מחייב כדי לעצור drift. |
| **הפניה** | [`../backend/scripts/export_openapi.py`](../backend/scripts/export_openapi.py), [`../.github/workflows/openapi-contract.yml`](../.github/workflows/openapi-contract.yml), [`../Makefile`](../Makefile), [`../frontend/.gitignore`](../frontend/.gitignore) |

---

## Auth forms — react-hook-form + zod

| | |
|--|--|
| **בעיה** | ניהול ידני/לא אחיד במסכי auth יוצר boilerplate וחזרתיות, ומגדיל סיכון לסטיות בין validation לבין submit state. |
| **החלטה** | לאחד את `Login`/`Register`/`VerifyEmail` תחת `react-hook-form` + `zodResolver`, עם סכמות ייעודיות לכל מסך ושמירת JSX/CSS ו-auth/navigation flow ללא שינוי. |
| **שימור behavior** | `Login` שומר `defaultValues` מ-`state?.email`; `Register` מחבר `PhoneInput` דרך `Controller`; `VerifyEmail` משאיר `resendLoading` נפרד ו-`formState.isSubmitting` ל-verify בלבד; שגיאות API נשארות ב-`error` state נפרד. |
| **יתרון** | קוד עקבי יותר בין כל מסכי auth, הפרדת אחריות נקייה (validation מול API errors), ותחזוקה פשוטה יותר להרחבות עתידיות. |
| **Trade-off** | תלות נוספת בפרונט ודורש משמעת סכמות/טיפוסים כדי להימנע מ-drift בין schema לשדות UI. |
| **הפניה** | [`../frontend/src/pages/Login.tsx`](../frontend/src/pages/Login.tsx), [`../frontend/src/pages/Register.tsx`](../frontend/src/pages/Register.tsx), [`../frontend/src/pages/VerifyEmail.tsx`](../frontend/src/pages/VerifyEmail.tsx), [`../frontend/package.json`](../frontend/package.json) |

---

## AdminLookup on-demand fetch — `useMutation` (React Query)

| | |
|--|--|
| **בעיה** | `AdminLookup` עבד עם manual async/state (`idle/loading/ready/error`) למרות שמדובר ב-trigger יזום משתמש (lookup לפי מזהה בלחיצה), מה שיצר state-machine אד-הוק מחוץ ל-RQ conventions. |
| **החלטה** | להעביר את flow ל-`useMutation` נפרד ל-ride ול-booking lookup, עם state נגזר מ-`isPending/isError/data` במקום `Result` ידני. |
| **שימור behavior** | UI נשאר זהה: אותם placeholders, כפתורים, הודעות `idle/loading/error`, ו-JSON output. ללא שינוי CSS. |
| **למה** | זה pattern נכון ל-imperative on-demand fetch ב-TanStack Query, מפחית state ידני, ומשפר עקביות ארכיטקטונית במסכי admin. |
| **Trade-off** | נוסף coupling קטן ל-RQ mutation state במסך יחיד, אבל הפחתת ה-boilerplate והסיכון ל-state drift עדיפה. |
| **הפניה** | [`../frontend/src/features/admin/pages/AdminLookup.tsx`](../frontend/src/features/admin/pages/AdminLookup.tsx), [`../frontend/src/features/admin/api/lookup.ts`](../frontend/src/features/admin/api/lookup.ts) |

---

<a id="prometheus-grafana"></a>

## Prometheus + Grafana monitoring

| | |
|--|--|
| **בעיה** | `health` ולוגים עוזרים ל-diagnosis, אבל חסרים time-series metrics (RPS, latency, 5xx trend) ו-dashboard תפעולי רציף. |
| **החלטה** | `prometheus-fastapi-instrumentator` בבקאנד: חשיפת `/metrics` מ-`main.py`. ב-Compose נוספו שירותי `prometheus` ו-`grafana` תחת profile ייעודי `monitoring`, עם provisioning מוכן (`datasource + dashboard provider`) ו-dashboard בסיסי (`HTTP Requests/sec`, `p95`, `5xx`, `in-progress`). |
| **אלטרנטיבות** | (1) Datadog/NewRelic SaaS — מהיר יותר להתחלה אבל יקר יותר לסקייל וריבוי סביבות. (2) OpenTelemetry full stack — גמיש מאוד אך מורכב לשלב ראשון. (3) להישאר עם health+logs בלבד — פחות ראות מגמות. |
| **יתרון** | Visibility מיידי על ביצועי API, קל להרחיב ל-Redis/RabbitMQ/DB metrics בהמשך; profile `monitoring` שומר את סביבת dev קלה כשלא צריך observability stack. |
| **Trade-off** | Dashboard ראשוני ממוקד HTTP בלבד; queries תלויות naming של metrics מה-instrumentator ועלולות לדרוש התאמות לפי גרסה. |
| **Interview pitch (≈30s)** | *"הוספתי Prometheus ו-Grafana עם profile ייעודי ב-compose, וחשפתי `/metrics` בבקאנד. זה נותן baseline של RPS, p95, error rate ו-in-flight requests בלי להעמיס על סביבת פיתוח כשלא צריך."* |
| **הפניה** | [`../backend/app/main.py`](../backend/app/main.py), [`../docker-compose.yml`](../docker-compose.yml), [`../monitoring/prometheus.yml`](../monitoring/prometheus.yml), [`../monitoring/grafana/dashboards/linkup.json`](../monitoring/grafana/dashboards/linkup.json) |

---

<a id="slos-error-budgets"></a>

## SLOs & Error Budgets

| | |
|--|--|
| **בעיה** | dashboards ולוגים נותנים observability, אבל בלי יעדי שירות רשמיים קשה להחליט מתי המערכת “מספיק יציבה” ומתי לעצור rollout בגלל אמינות. |
| **החלטה** | להגדיר SLO framework מעל metrics הקיימים: backend latency/availability + worker reliability counters (RabbitMQ/Outbox/AI/Billing). המדיניות מתורגמת ל-error budget חודשי שמנווט החלטות delivery. |
| **אלטרנטיבות** | (1) לפעול לפי alerts בלבד. (2) להסתמך על “health=ok” בלי SLA/SLO. (3) SRE פורמלי כבד מדי מוקדם מדי. |
| **יתרון** | יישור בין product למהנדסים: ברור מתי ממשיכים לפיצ'רים ומתי משקיעים באמינות; התראות הופכות לפעולה מדידה ולא “תחושת בטן”. |
| **Trade-off** | דורש תחזוקה של dashboards/alerts ושיפור מתמיד של SLI definitions כדי להימנע מ-targets לא ריאליים. |
| **Interview pitch (≈30s)** | *"אחרי שהטמענו metrics בבקאנד ובעובדים, הוספנו שכבת SLOs: availability + p95/p99 + async success ratio עם error budget חודשי. זה נותן governance לפרודקשן — לא רק לראות גרפים אלא גם להחליט מתי לעצור rollout ולתקן אמינות."* |
| **הפניה** | [`../backend/app/infrastructure/metrics.py`](../backend/app/infrastructure/metrics.py), [`../backend/app/workers/notification_worker.py`](../backend/app/workers/notification_worker.py), [`../backend/app/workers/task_worker.py`](../backend/app/workers/task_worker.py), [`../backend/app/workers/ai_worker.py`](../backend/app/workers/ai_worker.py), [`../monitoring/prometheus.yml`](../monitoring/prometheus.yml) |

---

<a id="chat-inbox-n1"></a>

## Chat inbox: batched aggregate (N+1 fix)

| | |
|--|--|
| **בעיה** | `list_my_conversations` קראה ל-`get_last_message` + `has_unread_messages` **לכל שיחה בנפרד** → 2N+ DB round-trips כשלמשתמש יש N שיחות. |
| **החלטה** | פונקציה חדשה `get_inbox_aggregates` ב-`chat/crud.py`: שלוש שאילתות מאוגדות (last message per conversation, last incoming per conversation, last_read_at per participant) + מיזוג בזיכרון. הרשימה נמשכת בעמודים דרך `list_conversations_paginated`; **`list_my_conversations` קוראת לה רק על `conversation_id`-ים של העמוד** (לא על כל האינבוקס בבת אחת). |
| **אלטרנטיבות** | (1) `joinedload` ב-ORM — לא מספיק: לא מחשב `has_unread` ב-SQL. (2) GraphQL + DataLoader — overkill לממשק REST הנוכחי. (3) view materialised ב-Postgres — מורכבות תפעולית גבוהה, stale data. |
| **יתרון** | מ-~3N קריאות (לעומת N שיחות **בעמוד**) ל-**4 קריאות קבועות לעמוד**; `get_last_message` + `has_unread_messages` המקוריות נשמרות לשימושים אחרים (DRY). |
| **Trade-off** | שאילתות ה-aggregate ארוכות יותר (subquery + join); אם inbox ריק — early return מיידי. |
| **Interview pitch (≈30s)** | *"ה-inbox הריץ get_last_message + has_unread לכל שיחה — N+1 קלאסי. החלפתי באגרגציה אחת שמריצה שלוש שאילתות מאוגדות ומאחדת בזיכרון, ועם pagination האגרגציות רצות רק על השיחות בעמוד. מ-3N ל-4 קריאות קבועות לעמוד."* |
| **הפניה** | [`../backend/app/domain/chat/crud.py`](../backend/app/domain/chat/crud.py) (`get_inbox_aggregates`), [`../backend/app/domain/chat/service.py`](../backend/app/domain/chat/service.py) (`list_my_conversations`) |

---

<a id="chat-detail-redundant-refetch"></a>

## Chat detail / booking-chat: redundant conversation re-fetch elimination

| | |
|--|--|
| **בעיה** | `get_or_create_conversation`, `get_or_create_conversation_by_booking`, ו-`get_conversation_detail` (`chat/service.py`) — כל אחד קרא ל-`_get_partner_last_read_at` ול-`_get_partner_read_up_to_message_id`, ששניהם ביצעו `get_conversation_by_id` **מחדש** כדי לחשב `partner_id`, למרות שה-conversation כבר נטען. סה"כ **2 שאילתות SELECT מיותרות + 2 שאילתות participant** (שאפשר למזג) → 5–7 queries per endpoint במקום 2–4. |
| **החלטה** | Helper יחיד `_get_partner_read_info(db, conversation_id, partner_id)` מחליף את שני ה-helpers; מקבל `partner_id` ישירות (שכבר זמין בשלושת ה-callers — `other_user_id` ב-2 הראשונים, `conv.user_id_2 if ... else conv.user_id_1` בשלישי) ומחזיר `(last_read_at, last_read_message_id)` ב-**שאילתה אחת** על `conversation_participants`. |
| **אלטרנטיבות** | (1) להעביר את ה-conversation object ל-helpers — מורכב יותר ולא חוסך את השאילתה הכפולה. (2) cache ב-session level — מסכן data staleness. |
| **יתרון** | 2 redundant `SELECT conversations + selectinload users` נעלמים + 2 participant queries מתמזגים ל-1 → מ-5–7 ל-2–4 queries per endpoint. |
| **הפניה** | [`../backend/app/domain/chat/service.py`](../backend/app/domain/chat/service.py) (`_get_partner_read_info`, `get_or_create_conversation`, `get_or_create_conversation_by_booking`, `get_conversation_detail`) |

---

<a id="chat-inbox-cursor-pagination"></a>

## Chat inbox: cursor pagination (keyset)

| | |
|--|--|
| **בעיה** | משיכת כל רשימת השיחות בבקשה אחת לא סקיילת; `OFFSET` גדול לא יציב. |
| **החלטה** | **`list_conversations_paginated`** — מיון לפי `COALESCE(conversations.last_message_at, conversations.created_at)` + `conversation_id DESC`, `LIMIT limit+1`, פילטר אחרי cursor ב-keyset; `last_message_at` נשמר ב-`create_message` עם עדכון מונוטוני (`GREATEST`) כדי לשמור סדר יציב תחת קונקרנציה. קידוד/פענוח cursor עבר ל-helper המשותף **`app/core/pagination/cursor.py`** (payload אטום, UTC normalization; בצ'אט נשמר `{"t","c"}`); תגובה **`PaginatedConversationsResponse`**; cursor לא תקין → **422** (`CHAT_INVALID_INBOX_CURSOR`). **`list_conversations_for_user`** נשאר ללא מחיקה לשימושים אחרים. פרונט: **`useInfiniteQuery`**, **`getNextPageParam` מ־`next_cursor`**, sentinel **`IntersectionObserver`** בתוך סיידבר עם גלילה. |
| **הפניה** | [`../backend/app/core/pagination/cursor.py`](../backend/app/core/pagination/cursor.py), [`../backend/app/domain/chat/crud.py`](../backend/app/domain/chat/crud.py) (`list_conversations_paginated`), [`../frontend/src/pages/Messages.tsx`](../frontend/src/pages/Messages.tsx), [`docs/architecture/API.md`](architecture/API.md) |

---

<a id="api-read-caps-batch-status"></a>

## API read caps + batch passenger-request status (notifications / cancel ride / groups)

| | |
|--|--|
| **בעיה** | חיפוש מרחבי בלי תקרה בעת יצירת בקשה או רענון התאמות; feed in-app של התראות משך את כל ה-bookings של הנוסע; `cancel_ride_and_bookings` ריצה פר־`request_id` (select+update); **ביטול בקשת נוסע** (`DELETE …/passengers/{id}/cancel`) היה לולאה על כל booking עם `execute_booking_cancellation` → ~O(N) שאילתות + עדכוני `PassengerRequest` מיותרים לפני `status=CANCELLED`; `get_my_groups` — N+1 על `get_member_count`. |
| **החלטה** | **`_IMMEDIATE_MATCH_LIMIT = 20`** ב־`passengers/service.py` על `find_rides_by_coordinates` ב־`create_passenger_request` / `get_matches_by_request_id`. פיד ההתראות (**`GET /users/me/notifications`**) עבר ל-**cursor pagination**: `limit` (default 20, max 100), `after`, תגובה `items`/`next_cursor`/`has_more`/`limit`. ב-CRUD שני מקורות ההתראות (`get_user_bookings_with_relations`, `get_all_pending_bookings_for_driver`) עובדים ב-keyset עם `ORDER BY created_at DESC, booking_id DESC`, פילטר `after=(created_at, booking_id)`, ו-`limit+1`; ב-service מתבצע merge+sort אחיד ואז חישוב cursor דרך helper משותף (`app/core/pagination/cursor.py`). אחרי ביטול נסיעה: **select אחד** `Booking` עם `request_id IN (...)`, חישוב סטטוס מ־**`_status_from_bookings_list`** (מקור יחיד שממנו גם **`determine_passenger_request_status`**), ואז **`bulk_update_requests_status`** לפי קבוצות סטטוס. **ביטול בקשת נוסע:** **`bulk_cancel_bookings_for_request`** — אגרגציה של מושבים לפי נסיעה (סטטוסים שתפסו מקום), **`FOR UPDATE`** על `rides`, עדכון **`UPDATE bookings … request_id`** אחד; `PassengerRequest.status=CANCELLED` נשאר ב-service. מיגרציה **019** מוסיפה ל-PostgreSQL את ערכי **`en_route` / `arrived` / `trip_in_progress`** ב-`booking_status` (תואם ל-Python `BookingStatus`). קבוצות: **`get_member_counts_batch`** (`GROUP BY`) + שימוש ב־`get_my_groups`. |
| **Trade-off** | ה-badge בפרונט נשאר מבוסס עמוד ראשון (`limit=20`) עם read-state מקומי (localStorage), ולכן לא מייצג ספירה מוחלטת של כל היסטוריית ההתראות — זה מחיר מודע עד מעבר עתידי לשרת עם `read_state` קנוני. |
| **הפניה** | [`../backend/app/domain/passengers/service.py`](../backend/app/domain/passengers/service.py), [`../backend/app/domain/bookings/crud.py`](../backend/app/domain/bookings/crud.py), [`../backend/app/domain/groups/crud.py`](../backend/app/domain/groups/crud.py), [`docs/architecture/API.md`](architecture/API.md) |

---

<a id="geo-manifest-passenger-reads"></a>

## זרימת preview גיאוגרף + תקרות קריאה (מניפסט נהג / בקשות נוסע)

| | |
|--|--|
| **בעיה** | **`get_full_routing_data`** (`processor.py`) קרא ל-Google Geocoding ישירות משני צירי טקסט ובכך דילג על שכבת **`geocode_cache`** (Redis + **`get_or_compute`**). **`get_ride_manifest`** טען את כל ה-PENDING/CONFIRMED ללא תקרה. **`GET /passenger/passengers/me`** החזיר רשימה לא מוגבלת לעומס זיכרון/API בנוסע עם היסטוריה ארוכה. |
| **החלטה** | **Preview:** `processor.get_full_routing_data` משתמש ב-**`geocode_cache.get_coordinates`** למוצא ויעד לפני Directions. **מניפסט:** ספירות סטטוס + **SELECT** יחיד עם מיון **`CASE` (confirmed לפני pending)**, **`.limit(MANIFEST_BOOKING_ROW_LIMIT)`** (100 ב-[`../backend/app/core/constants.py`](../backend/app/core/constants.py)); תגובה כוללת **`confirmed_total`**, **`pending_total`**, **`manifest_truncated`**, ו-**`total_confirmed_passengers`** כספירת מאושרים ב-DB (**`BookingReadsService`**). **בקשות נוסע (`GET /passenger/passengers/me`):** מעבר מ-offset/page ל-**cursor pagination** (`cursor`, `limit` -> `items`, `next_cursor`, `has_more`) עם keyset יציב `requested_departure_time DESC, request_id DESC`; פרונט: **`fetchMyPassengerRequests`** + **`useMyRequests`** עם `useInfiniteQuery`. OpenAPI: בעקבות [Stage 2 של `OpenAPI snapshot code generation`](#openapi-snapshot-code-generation-orval) הסכמה מיוצאת אוטומטית דרך **`make openapi`** — אין יותר patch ידני על snapshot. |
| **Trade-off** | מניפסט מקוצר עלול להסתיר PENDING אם יש יותר מ-100 צירופי pending+confirmed — לשקול UI "עמוד נוסף" אם יידרש מוצרית. |
| **הפניה** | [`../backend/app/domain/geo/processor.py`](../backend/app/domain/geo/processor.py), [`../backend/app/infrastructure/geo/geocode_cache.py`](../backend/app/infrastructure/geo/geocode_cache.py), [`../backend/app/domain/bookings/booking_reads_service.py`](../backend/app/domain/bookings/booking_reads_service.py), [`../backend/app/domain/passengers/router.py`](../backend/app/domain/passengers/router.py), [`docs/architecture/API.md`](architecture/API.md), [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) |

---

<a id="my-bookings"></a>

## My Bookings: aggregated reads (דילוג על N+1)

| | |
|--|--|
| **בעיה** | בטאב "הזמנות שלי" מספר קריאות per booking/ride יוצרות N+1 ו-UX איטי. |
| **החלטה** | Read models מאוגדים לנהג ולנוסע; **הפרדת פעיל מול היסטוריה**: `GET …/driver-summary/active` + `…/driver-summary/history` (ומקבילים לנוסע) עם **קורסור** (`after` + `next_cursor`, Base64 JSON ב־UTC דרך [`core/pagination/cursor.py`](../backend/app/core/pagination/cursor.py)). **Legacy** `GET …/driver-summary` ו-`…/passenger-summary` נשמרים לתאימות ומסומנים **deprecated** ב-FastAPI/OpenAPI. |
| **אלטרנטיבות** | (1) GraphQL עם DataLoader. (2) BFF שמרכז. (3) N+1 עם `joinedload` — עדיין הרבה round-trips אם ה-UI שואל "פר booking". (4) רק endpoint אחד ללא פיצול — payloads בלתי חסומים בהיסטוריה. |
| **יתרון** | מעט round-trips לפעיל; היסטוריה מדורגת; פחות זיכרון/רשת; נוסעים בהיסטוריית נהג נטענים עם `with_loader_criteria` מתאים (לא רק pending/confirmed). |
| **Trade-off** | יותר נתיבים ומפתחות React Query (`driverActive` / `driverHistory` וכו’). |
| **Interview pitch (≈30s)** | *"במקום N+1 יש read models; לפעיל תקרה רכה ולפעמים שני מפתחות cache; היסטוריה עם cursor כמו inbox."* |
| **הפניה** | HIGHLIGHTS, `BookingReadsService`, [architecture/API.md](architecture/API.md), [architecture/DATABASE.md](architecture/DATABASE.md) |

---

<a id="idempotency"></a>

## Idempotency-Key — `request-ride-from-search`

| | |
|--|--|
| **בעיה** | double tap / retry רשת → שתי bookings לאותו ride. |
| **החלטה** | Header אופציונלי, Redis `SET NX`, fingerprint לגוף, cache רק **201**; 409+Retry-After בזמן processing; **fail-open** בלי Redis. |
| **אלטרנטיבות** | (1) unique constraint DB בלבד — לא מכסה כל מרוץ. (2) idempotency רק בפרונט — לא אמין. |
| **יתרון** | אותו דפוס שמסחר אלקטרוני מכיר; לא שיניתי `BookingService.request_to_join` ללוגיקה, רק הכניסה. |
| **Trade-off** | בלי Redis אין dedup. |
| **Interview pitch (≈30s)** | *"Stripe-style: `SET NX` + fingerprint, שומרים רק תשובה מוצלחת. בלי Redis — fail-open כי זמינות מול dedup."* |
| **הפניה** | ADR §19, HIGHLIGHTS §7ה / 0א |

---

<a id="passenger-search-vs-save"></a>

## נוסע — חיפוש נסיעות מול שמירת בקשה והתראה (`ride.created`)

| | |
|--|--|
| **בעיה** | נוסע רוצה לראות נסיעות זמינות בלי “לזהם” את ה-DB; וגם לקבל התראה כשנהג מפרסם נסיעה שמתאימה לפרופיל/מיקום. |
| **החלטה** | **חיפוש בלבד** — `GET /passenger/passengers/search-rides`: שאילתה (PostGIS / פילטרים), **בלי** `INSERT` ל־`passenger_requests`. **שמירה + מנוי להתאמות** — `POST /passenger/passengers/` עם `PassengerRequestCreate` (`is_notification_active`, `group_id` אופציונלי) — אותו מודל בקשה גם ל-matching מיידי. **התראות אסינכרוניות:** אחרי יצירת נסיעה נרשם ב־Outbox **`ride.created`**; `notification-worker` מפרסם ל־RabbitMQ; **`handle_ride_created`** טוען את הנסיעה, מריץ `find_passengers_for_ride_notification` (סינון פעיל/התראות/תאריכים/`group_id`/קרבה גיאוגרפית), ולכל נוסע מתאים מפעיל את שכבת ההתראות עם אירוע פנימי **`ride.created_for_passengers`** (מייל Brevo וכו’) — **לא** אותו routing key כמו `ride.created`. |
| **עדכון pagination/filters** | cursor של `search-rides` הוקשח ל-**opaque token** (`after: str`, `next_cursor`) עם decode ב-service ו-keyset ישיר ב-CRUD על `(Ride.departure_time, Ride.ride_id)` — ללא lookup נוסף לפי `ride_id` קיים. שגיאת cursor לא תקין מוחזרת כ-**422** (`INVALID_SEARCH_CURSOR`). בנוסף, נוספה תמיכה מלאה ב-**`destination_radius`** (ק״מ) כרדיוס יעד נפרד; אם קיים הוא מחליף רק את רדיוס תנאי היעד ב-`ST_DWithin`, בעוד `search_radius` ממשיך לרדיוס הכללי/מוצא. |
| **אלטרנטיבות** | (1) לשמור כל חיפוש כ־row — רעש ועומס DB. (2) התראות בלי שורת בקשה — קשה לביטול/הרשאות. |
| **יתרון** | הפרדה ברורה בין צפייה חד־פעמית לבין מנוי אירועים; מקור אמת אחד ל־`passenger_requests` גם ל־matching וגם לתור התראות. |
| **Trade-off** | שני מסלולי API לנוסע — דורש מוצר/תיעוד ברורים כדי שלא יבלבלו משתמשים. |
| **Interview pitch (≈35s)** | *"חיפוש הוא read-only; רק POST יוצר בקשה שנכנסת לתזמורת התראות. כשנהג יוצר נסיעה — Outbox שולח `ride.created`, וה-worker מסנן נוסעים רלוונטיים ואז שולח מייל דרך אירוע פנימי לתבניות — בלי לערבב את שם האירוע ב-Rabbit."* |
| **הפניה** | ADR §17, [architecture/EVENTS.md](architecture/EVENTS.md) (זרימת `ride.created` / `ride.created_for_passengers`), [`notification_tasks.py`](../backend/app/workers/tasks/notification_tasks.py) |

---

<a id="chat-message-idempotency"></a>

## Idempotency-Key — `POST …/chat/conversations/{id}/messages`

| | |
|--|--|
| **בעיה** | double tap / retry רשת → שתי הודעות DB לאותה כוונה בשיחה. |
| **החלטה** | כותרת אופציונלית, מפתח Redis נפרד (`idempotency:chat_message:{user_id}:{key}`), fingerprint על `conversation_id` + תוכן; cache רק **201**; 409/`Retry-After` בזמן processing; **fail-open** בלי Redis — אותם עקרונות כמו §19. |
| **אלטרנטיבות** | (1) idempotency רק ב-UI — לא אמין. (2) unique digest ב-DB — דורש schema + edge cases למחיקות. |
| **יתרון** | אותו story כמו Stripe/e-commerce; `message_idempotency.py` + router דק בלי להזיז לוגיקת שמירה עמוקות. |
| **Trade-off** | בלי Redis אין dedup. |
| **Interview pitch (≈30s)** | *“החלפתי את אותה מסגרת Stripe-style מנסיעות לצ’אט: מפתח פר-משתמש, fingerprint על conversation+body, שומרים רק תשובת הצלחה.”* |
| **הפניה** | ADR §25, Frontend ADR §2, HIGHLIGHTS (Latest updates + §7ה); [Chat — optimistic outbound UI](#chat-optimistic-outbound); [`frontend/src/api/chat.ts`](../frontend/src/api/chat.ts), [`types/chatList.ts`](../frontend/src/types/chatList.ts), [`useMessageThread.ts`](../frontend/src/pages/MessageThread/useMessageThread.ts), [`useChatPopup.ts`](../frontend/src/components/ChatPopup/useChatPopup.ts), [`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts) |

---

<a id="refresh-token-hashed-storage"></a>

## M4 — Refresh token hashed at rest (SHA-256)

| | |
|--|--|
| **בעיה** | `users.refresh_token` שמר JWT refresh כ-plaintext ב-DB. דליפת DB = תוקף מחדש sessions ללא הגבלה. בנוסף, `authenticate_with_google` עקף את CRUD ישירות (`user.refresh_token = refresh_token`), וה-generic `update` לא חסם כתיבת plaintext ל-field. |
| **החלטה** | (1) `hash_refresh_token(token)` ב-`security.py` — SHA-256 (מתאים לטוקנים עם אנטרופיה גבוהה; bcrypt מיותר). (2) `CRUDUser.update_refresh_token` שומר hash בלבד — נקודת כתיבה אחת. (3) `CRUDUser.verify_refresh_token` — `hmac.compare_digest` (constant-time) — **service layer לא מייבא hash ולא יודע על מנגנון האחסון**. (4) `refresh_token` נוסף ל-`protected_fields` ב-generic `update` נגד bypass. (5) Google auth עובר דרך CRUD במקום השמה ישירה. (6) Migration **021**: NULL-ify כל הטוקנים הקיימים (לא ניתן ל-hash plaintext ללא deploy מתואם). |
| **אלטרנטיבות** | (1) bcrypt — overkill ו-latency מיותרת; refresh tokens הם JWTs עם 256+ bits entropy. (2) Hash existing tokens in migration — אפשרי אך דורש deploy מתואם (migration לפני קוד = breakage). (3) No hash — פשוט אבל "DB leak = game over". |
| **יתרון** | DB leak לא חושף tokens; service layer decoupled מ-hashing; constant-time comparison. |
| **Trade-off** | כל המשתמשים הקיימים מנותקים פעם אחת (re-login); SHA-256 לא מגן על tokens עם אנטרופיה נמוכה (לא רלוונטי — הם JWTs). |
| **Interview pitch (≈30s)** | *"refresh tokens היו plaintext ב-DB. העברתי ל-SHA-256 hash ב-CRUD layer אחד, עם constant-time compare ו-protected_fields נגד bypass — ה-service layer לא יודע שיש hash. מיגרציה 021 מנלנת את הקיימים כי אי אפשר ל-hash בלי deploy מתואם."* |
| **הפניה** | [`backend/app/core/security.py`](../backend/app/core/security.py) (`hash_refresh_token`), [`backend/app/domain/users/crud.py`](../backend/app/domain/users/crud.py) (`update_refresh_token`, `verify_refresh_token`, `protected_fields`), [`backend/app/domain/auth/service.py`](../backend/app/domain/auth/service.py), [`backend/alembic/versions/021_hash_existing_refresh_tokens.py`](../backend/alembic/versions/021_hash_existing_refresh_tokens.py) |

---

<a id="auth-session"></a>

## Auth: JWT + `jti` + denylist (logout)

| | |
|--|--|
| **בעיה** | JWT stateless — אחרי logout ה-access עדיין חתום עד `exp`. |
| **החלטה** | `jti` + `SETEX denylist:{jti}` ב-Redis עד `exp`; HTTP בודק; **fail-open** אם Redis down ב-read. |
| **אלטרנטיבות** | (1) session server-side (sticky). (2) רשימת ביטול ב-Postgres לכל request — עומס. (3) access קצר מאוד בלי denylist — UX גרוע. |
| **יתרון** | logout אמיתי על access בלי טבלת sessions גדולה. |
| **Trade-off** | בדיקות denylist בכל handshake מוסיפות תלות Redis במסלול WS auth; נבחר fail-open לשמירת זמינות אם Redis למטה. |
| **Interview pitch (≈30s)** | *"הוספתי jti ל-access ו-Redis denylist ב-logout גם ל-HTTP וגם ל-WS handshake. אם Redis נופל, בחרתי fail-open כדי לא ליפול גלובלית בזמינות."* |
| **הפניה** | ADR §18, HIGHLIGHTS §7ד |

---

<a id="circuit-breaker"></a>

## Circuit Breaker — Google Maps + Brevo email (באקאנד)

| | |
|--|--|
| **בעיה** | Geocoding/Directions איטי או 429 → storm של requests; Brevo down + Tenacity על ה-SDK → retries מציפים את הספק ואת ה-worker. |
| **החלטה** | מחלקה משותפת **`CircuitBreaker`** עם `Gauge` מוזרק; **גיאו:** מעגל in-memory לכל API — OPEN = אין HTTP ל-Google; **מייל:** `brevo_email_cb` — OPEN = `EmailProviderCircuitOpenError` בלי קריאה ל-Brevo (Tenacity רק כשהמעגל מאפשר). health מדווח `circuit_breakers` (כולל `brevo_email`) בלי לסמן את השרת unhealthy. |
| **אלטרנטיבות** | (1) Retry בלי cap — מחמיר. (2) rate limit בלבד. (3) sidecar (Envoy) — overkill. |
| **יתרון** | fail-fast; מגן על CPU ו-external budget; מדדי `geo_*` / `brevo_*` נפרדים. |
| **Trade-off** | מעגל **לא** משותף בין instances — reset אחרי deploy. |
| **Interview pitch (≈30s)** | *"מחלקה אחת, שני סוגי מדדים: גיאו — מעגל לכל API; Brevo — מעגל לפני ה-SDK. Health מציג מצב אבל status הכללי תלוי DB/Redis/Rabbit בלבד."* |
| **הפניה** | ADR §20, HIGHLIGHTS §0א, `docs/architecture/NOTIFICATIONS.md` |

---

<a id="geocode-cache-stampede"></a>

## Geocode cache — mutex נגד cache stampede (באקאנד)

| | |
|--|--|
| **בעיה** | cache לפי כתובת (TTL 24h) חוסך Google — אבל ב־**cold miss** או מיד אחרי פקיעות, מאות בקשות מקבילות לאותה מחרוזת כתובת יגרמו ל־**N קריאות Geocoding** במקביל (סערה על quota/latency). |
| **החלטה** | **`get_or_compute`** ב־[`cache_stampede.py`](../backend/app/infrastructure/redis/cache_stampede.py): נעילה פר־`cache_key`; מנצח מריץ `GeocodingService` ושומר ב־Redis; עוקבים ממתינים עם poll קצר; **fail-open** בחריג Redis — מתקדמים ישירות ל-Google בלי deadlock. Hits/misses: **`geo_cache_hits_total`** / **`geo_cache_misses_total`**; Mutex/stampede: **`cache_lock_acquired_total`**, **`cache_stampede_avoided_total`**, **`cache_fail_open_total`**. קריאות מ־[`geocode_cache.get_coordinates`](../backend/app/infrastructure/geo/geocode_cache.py). |
| **אלטרנטיבות** | (1) רק TTL בלי סנכרון — פשוט אבל storm על miss. (2) single-flight ב-process בלבד — לא מגן בתהליכי worker/API מרובים. |
| **יתרון** | פגיעות Google מוגבלות ל־אחד(ים) פר מפתח בזמני burst; משתלב עם **circuit breaker** ו־timeouts קיימים. |
| **Trade-off** | latency לעוקבים = זמני המתנה + Redis; מתקבל בהחלטה בהעדפת הגנה על upstream. |
| **Interview pitch (≈30s)** | *"לא הסתפקתי ב-TTL על גיאוקוד: בהעדר ערך, נעלתי לפי מפתח Redis ואיחדתי compute כדי שהגשם של בקשות מקביליות לא יהפוך לזליגה של quota ל-Google. יש Prometheus ל-hit/miss ולמה שנמנע."* |
| **הפניה** | [`MONITORING.md`](operations/MONITORING.md) §Geocode · [`HIGHLIGHTS`](ENGINEERING_HIGHLIGHTS.md) (Latest updates + טבלאות גיאו) · טסט: [`backend/tests/core_flows/test_geo_cache.py`](../backend/tests/core_flows/test_geo_cache.py) |

---

<a id="email-renderer"></a>

## Email: React Email / Node `email-renderer`

| | |
|--|--|
| **בעיה** | Jinja2 מקומי ב-Python — קשה sharing עם פרונט, preview, קומפוננטות. |
| **החלטה** | מיקרו-שירות Node: `POST /render` { template, props } → HTML; Outbox/notification שולחים. |
| **אלטרנטיבות** | (1) MJML static. (2) שליחה דרך SaaS. (3) Jinja2 ב-Python. |
| **יתרון** | קומפוננטות, SSR כמו React, הפרדת אחריות. |
| **Trade-off** | hop רשת נוסף, health, סדר on compose. |
| **Interview pitch (≈30s)** | *"רינדור מייל עבר ל-Node+React Email — אותו mindset כמו SSR, templates ב-TS. ה-Python נשאר לאורקסטרציה ו-Outbox."* |
| **הפניה** | ADR §5, HIGHLIGHTS (מייל / email-renderer) |

---

<a id="fcm"></a>

## Push: FCM data-only

| | |
|--|--|
| **בעיה** | שליטה ב-UX: Toast בחזית, SW ברקע, עקביות בין iOS/Web. |
| **החלטה** | שרת שולח `data` map בלבד; קליינט מפרש ל-Toast/צליל. SW config — מקור אמת אחד: `frontend/docker/firebase-messaging-sw.template.js`; Vite plugin ב-dev, `envsubst` ב-Docker. |
| **אלטרנטיבות** | (1) `notification` object של FCM — פחות שליטה אחידה. |
| **יתרון** | שליטה מלאה בטקסט, שפה, A/B, analytics. |
| **Trade-off** | יותר לוגיקה בקליינט. |
| **הפניה** | [FCM_SYSTEM_SUMMARY.md](FCM_SYSTEM_SUMMARY.md), [adr/FCM_AND_PUSH.md](adr/FCM_AND_PUSH.md) |

---

<a id="booking-cancelled-by-passenger"></a>

## Booking cancelled by passenger — notification to driver

| | |
|--|--|
| **בעיה** | כשנוסע מבטל הזמנה מאושרת, הנהג לא מקבל שום התראה — לא יודע שהתפנה מקום ושצריך לעדכן תכנון. |
| **החלטה** | אירוע חדש **`BOOKING_CANCELLED_BY_PASSENGER`** ב-`NotificationEvent`; מופעל רק כשנוסע (לא נהג) מבטל booking **מאושר** (`CONFIRMED`). ב-`cancel_booking()` — בדיקת `is_passenger and was_confirmed` → `publish_to_outbox` לפני `db.commit()`. |
| **אסטרטגיה** | `role: driver`, `builder: BookingBuilder`, `template: passenger_cancelled`, `channels: [email, push, websocket]`. |
| **אלטרנטיבות** | (1) להתריע גם על ביטול PENDING — רעש מיותר לנהג. (2) רק מייל — חלון תגובה ארוך מדי. |
| **יתרון** | הנהג מקבל עדכון מיידי בשלושה ערוצים; אותו pipeline כמו שאר אירועי booking (outbox → worker → channels). |
| **Trade-off** | ביטול pending לא שולח התראה — בחירה מודעת להפחתת רעש. |
| **הפניה** | [`backend/app/domain/bookings/service.py`](../backend/app/domain/bookings/service.py) (`cancel_booking`), [`backend/app/domain/notifications/constants.py`](../backend/app/domain/notifications/constants.py), [`backend/app/domain/notifications/config/mappings.py`](../backend/app/domain/notifications/config/mappings.py), [architecture/EVENTS.md](architecture/EVENTS.md) |

---

<a id="reminder-push-channel"></a>

## Scheduled reminders — push channel

| | |
|--|--|
| **בעיה** | תזכורות לנוסע ולנהג נשלחו רק במייל — שיעור פתיחה נמוך, חלון תגובה ארוך (30 דקות לפני נסיעה). |
| **החלטה** | הוספת **`push`** לערוצי שני אירועי תזכורת (`PICKUP_REMINDER_PASSENGER`, `RIDE_START_DRIVER`); תבניות push חדשות `reminder_passenger` ו-`reminder_driver` ב-`push_conf.py`. |
| **יתרון** | התראת מערכת מיידית למכשיר — גם אם המייל לא נפתח בזמן. |
| **Trade-off** | שני ערוצים מקבילים יכולים ליצור "כפילות" תחושתית; push הוא ephemeral ומייל הוא persistent — משלימים זה את זה. |
| **הפניה** | [`backend/app/domain/notifications/config/mappings.py`](../backend/app/domain/notifications/config/mappings.py), [`backend/app/domain/notifications/config/templates_map/push_conf.py`](../backend/app/domain/notifications/config/templates_map/push_conf.py), [FCM_SYSTEM_SUMMARY.md](FCM_SYSTEM_SUMMARY.md) §8 |

---

## איך זה יושב מול High ו־ADR

- **השתמש ב-FEATURE_DECISIONS** כששואלים: *"למה לא X?"* — עמודת **אלטרנטיבות** + **Trade-off**.
- **השתמש ב-ENGINEERING_HIGHLIGHTS** לקישור לנתיבי קבצים ומספור סעיפים.
- **השתמש ב-ADR** כששואלים deep dive (מספור §).

[← חזרה ל-Interview Playbook](internal/INTERVIEW_PLAYBOOK.md)

---

<a id="pgbouncer"></a>

## PgBouncer (EC2 + Docker Compose)

| | |
|--|--|
| **בעיה** | כמה services (backend + workers) עם pools נפרדים יוצרים fan-out לחיבורי Postgres תחת עומס/redeploy. ב-EC2 בינוני זה פוגע בזיכרון/latency לפני CPU saturation. |
| **החלטה** | להוסיף `pgbouncer` כ-service פנימי ב-Compose (transaction mode), ולהעביר runtime services ל-`POSTGRES_HOST=pgbouncer`. |
| **אלטרנטיבות** | (1) להגדיל רק `max_connections` ב-Postgres — מטפל סימפטום ולא שורש. (2) בלי pooler, רק להקטין `DB_POOL_*` — עוזר חלקית. (3) RDS Proxy/managed pooler — עדיף בענן מנוהל אבל לא quickest win ב-EC2 קיים. |
| **מה סניור עושה (לא טריוויאלי)** | (1) `migrate` נשאר direct ל-`db` ולא דרך pooler. (2) asyncpg statement cache מנוטרל (`statement_cache_size=0`) לתאימות transaction pooling. (3) PgBouncer internal-only בלי פתיחת `6432` לציבור. (4) right-size ל-SQLAlchemy pools כדי להימנע מ-double-pooling אגרסיבי. (5) אם images ציבוריים דורסים config דרך entrypoint — עוברים ל-custom image מבוקר במקום workaround שביר. (6) מבטלים bind-mount ל-`userlist.txt`: הקובץ נוצר בתוך הקונטיינר בזמן startup מ-`POSTGRES_*` + `PGBOUNCER_ADMIN_PASSWORD`, וכך אין תלות UID/GID מול host. (7) **LISTEN/NOTIFY ל-outbox** לא דרך PgBouncer: `OutboxListener` ב-`run_outbox_worker` משתמש ב-**`DATABASE_URL_DIRECT`** (`POSTGRES_HOST_DIRECT` / `POSTGRES_PORT_DIRECT`) כי transaction pooling לא מעביר NOTIFY ללקוח — אחרת נשארים על polling איטי. |
| **יתרון** | connection storms נבלמים מוקדם, יותר יציבות בזמן deploys, ו-headroom להמשך scaling בלי שינוי לוגיקה דומיינית. |
| **Trade-off** | עוד רכיב תפעולי לנטר (health/config/auth), אבל זרימת הסודות פשוטה ועמידה יותר כי יצירת `userlist` עברה לתוך הקונטיינר במקום CI/host. |
| **Interview pitch (≈30s)** | *"במקום שכל service יפציץ את Postgres בחיבורים, הוספתי PgBouncer כ-layer פנימי. השארתי migrations direct ל-db, כיביתי statement cache ב-asyncpg, והקטנתי pools אפליקטיביים — זה בדיוק ההבדל בין 'להוסיף container' לבין rollout יציב ברמת production."* |
| **הפניה** | `docker-compose.yml`, `backend/app/db/session.py`, `backend/app/core/config.py` (`DATABASE_URL_DIRECT`), `backend/app/workers/outbox_worker.py`, `infrastructure/pgbouncer/{Dockerfile,pgbouncer.ini,userlist.txt.template,entrypoint.sh}`, `.github/workflows/backend-ci.yml`, `scripts/ops/pgbouncer-smoke.sh`, `backend/.env.example` (שדות `PGBOUNCER_ADMIN_PASSWORD`, `SENTRY_REPORT_URI`, `POSTGRES_HOST_DIRECT`, `POSTGRES_PORT_DIRECT`) |

---

<a id="redis-single-node"></a>

## Redis single-node reliability (EC2 + Docker Compose)

| | |
|--|--|
| **בעיה** | Redis מחזיק cache, denylist, idempotency, rate-limit ו-pub/sub לצ'אט. על single-host EC2, Sentinel בתוך אותו host לא מספק HA אמיתי מול נפילת המכונה, אבל כן מוסיף footprint, קונפיג ונתיבי failover שקשה לתפעל. |
| **החלטה** | לחזור לטופולוגיית Redis יחידה (`redis`) עם persistence (`appendonly yes`, `appendfsync everysec`, RDB snapshots), healthcheck ו-smoke ייעודי; לשמר הפרדת DB לוגית: **DB 0** ל-cache/rate-limit/idempotency/denylist ו-**DB 1** לצ'אט/pubsub/presence. |
| **אלטרנטיבות** | (1) ElastiCache/Managed Redis — עדיף כשעוברים ל-managed infra או multi-AZ. (2) failover מקומי בתוך אותו host — failover תהליכי בלבד, לא פותר host failure. (3) Redis Cluster — מורכב יותר מהצורך הנוכחי (key/value + pub/sub, בלי sharding אמיתי). |
| **מה סניור עושה (לא טריוויאלי)** | (1) מפשט topology במקום להציג HA מדומה. (2) שומר DB split כדי לא לערבב chat/pubsub עם cache/rate-limit. (3) מחבר `chat-ws` ב-`go-redis` `NewClient` דרך `REDIS_ADDR`, תוך שימוש ב-`REDIS_URL` לפרטי password/DB. (4) משאיר Redis clients fail-open איפה שההגנה היא defense-in-depth, כמו rate limit/geo cache. |
| **יתרון** | פחות שירותים, פחות drift בפריסה, קל יותר לתפעול על `t3.medium`, ועדיין יש durability בסיסית לנתונים זמניים/אופרטיביים. |
| **Trade-off** | Redis נשאר תלוי ב-host יחיד; HA אמיתי ידרוש managed Redis / multi-node מחוץ לשרת היחיד. |
| **Interview pitch (≈30s)** | *"בהתחלה בדקתי Sentinel, אבל על EC2 יחיד זה HA מדומה: אם ה-host נופל גם Sentinel נופל. לכן פישטתי ל-Redis יחיד עם AOF/RDB, healthcheck ו-smoke, ושמרתי DB split בין cache/rate-limit לבין chat pub/sub. זו החלטה תפעולית שמעדיפה אמינות אמיתית ופחות מורכבות עד מעבר ל-managed Redis."* |
| **הפניה** | `docker-compose.yml`, `backend/app/infrastructure/redis/{client.py,chat_pubsub.py,broadcast.py}`, `chat-ws/cmd/server/main.go`, `scripts/ops/redis-smoke.sh` |

---

<a id="rabbitmq-self-healing"></a>

## RabbitMQ self-healing consumer loop

| | |
|--|--|
| **בעיה** | אחרי ניתוק/סגירת channel, iterator של `aio_pika` יכול להיסגר ו-consumer להפסיק לעבוד עד restart חיצוני. |
| **החלטה** | `consume()` הפך ללולאת self-healing: recreate iterator/channel, bounded backoff על `_setup()` failures, draining מסודר, ומדד אופרטיבי `rabbitmq_consumer_iterator_restarts_total`. |
| **אלטרנטיבות** | (1) להסתמך רק על supervisor restart. (2) ליצור consumer חדש בכל restart חיצוני בלי recovery פנימי. |
| **יתרון** | עמידות טובה יותר לבעיות Rabbit transient בלי dependency על restart orchestration. |
| **Trade-off** | מורכבות לולאת consume עולה ודורשת observability כדי להבחין בין transient noise לבין תקלה כרונית. |
| **Interview pitch (≈30s)** | *"במקום שריסטארט תהליך יהיה הפתרון, ה-consumer מרפא את עצמו: אם iterator נסגר הוא נבנה מחדש עם backoff ומדד iterator restarts. כך מפחיתים downtime שקט של תורים."* |
| **הפניה** | `backend/app/infrastructure/rabbitmq/consumer.py`, `backend/app/infrastructure/metrics.py` |

---

<a id="frontend-runtime-config"></a>

## Frontend runtime config (12-factor)

| | |
|--|--|
| **בעיה** | `import.meta.env` ב-Vite מחליף ערכים בזמן build; image שנבנה בלי `VITE_*` גורם לפרונט שבור (`projectId` חסר ב-Firebase). |
| **החלטה** | לעבור ל-runtime config: entrypoint מייצר `config.js` + `firebase-messaging-sw.js` עם `envsubst`; הקוד קורא `window.__APP_CONFIG__` עם fallback ל-`import.meta.env` בדב. **`firebase-messaging-sw.js`** — מקור אמת אחד: [`frontend/docker/firebase-messaging-sw.template.js`](../frontend/docker/firebase-messaging-sw.template.js); ב-dev/build: Vite plugin **`firebaseSwPlugin`** (`vite.config.ts`, hook `buildStart`, `loadEnv`) מחליף placeholders `${VITE_*}` וכותב ל-`public/`; ב-Docker: `envsubst` ב-`40-render-config.sh`. הקובץ gitignored — אין Firebase config hardcoded ב-git. |
| **אלטרנטיבות** | (1) build-args + GH Secrets לכל VITE. (2) hardcode ציבורי בקוד. |
| **יתרון** | image agnostic לסביבה; שינוי קונפיג = restart, לא rebuild/pipeline. |
| **Trade-off** | עוד שכבת bootstrap בפרונט (template + entrypoint) וחובה לנהל env files בשרת בצורה עקבית. |
| **Interview pitch (≈30s)** | *"הוצאתי קונפיג פרונט מזמן build לזמן runtime. אותו image רץ בכל סביבה, וה-entrypoint מייצר config.js מה-env. זה 12-factor נקי ומונע drift בין builds."* |
| **הפניה** | `frontend/docker/40-render-config.sh` (**fail-fast** על מפתחות Firebase חובה; **defaults** לערכים אופציונליים), `frontend/src/config/runtime.ts`, `frontend/vite.config.ts` (**`firebaseSwPlugin`**), `docker-compose.yml` (**`frontend`** עם **`env_file: ./frontend/.env`** בפרופיל prod) |

---

<a id="deploy-env-sot"></a>

## Deploy env single source-of-truth (multi env-file + JWT sync)

| | |
|--|--|
| **בעיה** | Compose interpolates env from selected env-file בלבד; בלי `frontend/.env` ערכי `VITE_*` לא נטענים, ובלי סנכרון סודות אפשר mismatch בין backend/chat-ws. |
| **החלטה** | deploy script משתמש ב-`--env-file backend/.env --env-file frontend/.env`, מוסיף fail-fast guards לקבצים חסרים, ומסנכרן `JWT_SECRET` ב-`chat-ws/.env` מתוך `backend SECRET_KEY`. |
| **אלטרנטיבות** | (1) root `.env` ענק לכל השירותים. (2) GH Secrets ל-VITE ציבוריים. (3) סנכרון ידני של JWT בין קבצים. |
| **יתרון** | source-of-truth ברור לכל שכבה + הפחתת config drift בפריסות. |
| **Trade-off** | יש תלות במשמעת ops סביב `.env.production` לכל שירות ו-copy step תקין לפני compose up. |
| **Interview pitch (≈30s)** | *"חילקנו env לפי גבולות שירות אבל פריסה מרכיבה אותם במפורש. זה שומר runtime deterministic וגם מונע JWT mismatch בין backend ל-chat-ws."* |
| **הפניה** | `.github/workflows/backend-ci.yml`, `docker-compose.yml` |

---

<a id="oauth-popup-coop"></a>

## OAuth popup compatibility (COOP/COEP headers)

| | |
|--|--|
| **בעיה** | Google OAuth popup עלול להיחסם ל-`window.postMessage` בגלל מדיניות COOP קשיחה. |
| **החלטה** | הוספת headers ב-nginx: `Cross-Origin-Opener-Policy: same-origin-allow-popups` ו-`Cross-Origin-Embedder-Policy: unsafe-none` (עם `always`). |
| **אלטרנטיבות** | (1) לנסות flow בלי popup. (2) להחליש headers חלקית ברמת נתיב בלי ניתוח מלא של השפעה. |
| **יתרון** | תיקון יציב ל-flow OAuth הקיים בלי לשנות לוגיקת auth בפרונט/בקאנד. |
| **Trade-off** | מדיניות COOP/COEP פחות קשיחה לטובת תאימות OAuth popup. |
| **Interview pitch (≈30s)** | *"שגיאת popup postMessage נפתרה בשכבת ה-edge, לא ב-workaround בפרונט. הוספנו COOP/COEP תואם ל-Google popup תוך שמירה על HTTPS flow מלא."* |
| **הפניה** | `nginx/nginx.conf.template`, `scripts/ops/render-nginx-conf.sh` |

---

<a id="browser-csp-edge"></a>

## Browser CSP enforcement (Compose edge nginx)

| | |
|--|--|
| **בעיה** | פרונט הווב הוא **SPA סטטי** (Vite → `dist/`); בלי מדיניות דפדפן, XSS או טעינת משאבים מזויפים קלים יותר; Report-Only בלבד לא חוסם. |
| **החלטה** | **`nginx/nginx.conf.template`** (במאגר) + **`nginx/nginx.conf`** שנוצר בזמן ריצה (`gitignore`; פרופיל prod ב־Compose) מחזירים **`Content-Security-Policy`** מאוכפת עם allowlists צרות לפי צרכי המוצר (Firebase, Sentry, GA/GTM, maps, uploads, Stripe, Google Sign-In). **`report-uri`** מוזן מ־**`SENTRY_REPORT_URI`** ב־**`backend/.env`** (לא URL קשיח ב־Git). **`frame-src`** כולל `https://accounts.google.com` לצד Stripe. **בשכבת הסקריפטים:** הוסר **`'unsafe-inline'`** מ־**`script-src`**; Bootstrap לפני React (`linkup-lang` / `linkup-theme`) הועבר ל־**[`frontend/public/bootstrap.js`](../frontend/public/bootstrap.js)** והוא נטען ב־[`index.html`](../frontend/index.html) **לפני** **`/config.js`**. |
| **אלטרנטיבות** | (1) להישאר ב-Report-Only — בטוח יותר לגלגל אבל לא מגביל exploitability. (2) CSP דרך meta tag ב-HTML — פחות שליטה מרכזית מול edge. (3) nonces בלי SSR על ה-entry module — דורש rewrite דינמי של `index.html` או שירות edge (ראו **`docs/SECURITY_HEADERS.md`**). |
| **יתרון** | Defense-in-depth מול XSS לצד **`sanitizeHtml`**, **`react/no-danger`**, ודחיית HTML בצ'אט ב-API. |
| **Trade-off** | **`style-src`** עדיין כולל **`'unsafe-inline'`** (Vite/CSS); כל **inline script** חדש ב־HTML ידרוש hash או העברה לקובץ תחת **`'self'`**. |
| **Interview pitch (≈30s)** | *"הקשחנו XSS בשלוש שכבות: קלט טקסט בלבד בצ'אט, sanitization בפרונט, ו-CSP מאוכף ב-nginx עם דיווחים ל-Sentry — ומודעים שב-SPA בלי SSR, nonces דורשים עוד שכבה ב-edge."* |
| **הפניה** | `nginx/nginx.conf.template`, **`scripts/ops/render-nginx-conf.sh`**, **`docs/SECURITY_HEADERS.md`** |

---

<a id="single-ec2-cd"></a>

## Single-EC2 CD rolling deploy (no ALB)

| | |
|--|--|
| **בעיה** | Deploy ידני ב-SSH יוצר אי-עקביות וסיכון לטעות אנוש; Blue/Green מלא מכפיל משאבים ויקר מדי ל-`t3.medium`. |
| **החלטה** | ליישם CD פרגמטי: ה-workflows של השירותים עושים build+push ל-GHCR; **[`deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml)** (אחרי CI ירוק על `main`) מבצע deploy ל-EC2 ב-SSH, rollout ל-backend עם `docker compose up -d --no-deps backend`, health gate, rollback לתג קודם או ל-**`backend:latest`** אם התג הארכיון נעלם מהרישום. |
| **אלטרנטיבות** | (1) ALB + target groups + שני סטאקים — הכי נקי תיאורטית אבל תוספת עלות/מורכבות. (2) Blue/Green מקומי עם שני compose projects — כמעט פי 2 footprint בזמן rollout. (3) להישאר manual deploy — פשוט אך לא אמין לאורך זמן. |
| **מה סניור עושה (לא טריוויאלי)** | (1) משתמש ב-immutable `sha` ל-deterministic rollback. (2) שומר `previous tag` בצד השרת ולא מסתמך על `latest`. (3) deploy נחשב נכשל אם health לא עולה בזמן מוגדר. (4) מוסיף `stop_grace_period` ו-tuning בסיסי ב-nginx כדי לצמצם impact בזמן החלפה. |
| **יתרון** | תהליך פריסה אוטומטי, עקבי ומהיר, שמתאים לתקציב קטן ולשרת יחיד בלי לבנות פלטפורמה כבדה. |
| **Trade-off** | זה low-downtime ולא zero-downtime מוחלט, כי backend רץ כרגע בעותק יחיד בזמן ההחלפה. |
| **Interview pitch (≈30s)** | *"בחרתי CD פרגמטי לשרת יחיד: SHA-tag deploy + health gate + auto rollback. זה נותן אמינות תפעולית גבוהה בלי לשלם על ALB/תשתית כפולה, ומתאים לשלב הסקייל הנוכחי."* |
| **הפניה** | `.github/workflows/deploy-ec2.yml`, `.github/workflows/backend-ci.yml` (בנייה בלבד), `docker-compose.yml`, `nginx/nginx.conf.template`, `scripts/ops/render-nginx-conf.sh`, `docs/architecture/DEVELOPMENT.md` |

---

<a id="rate-limit-token-bucket"></a>

## Rate limiting — Token Bucket + Sliding Window (atomic Lua)

| | |
|--|--|
| **בעיה** | המימוש הקודם השתמש ב-`INCR + EXPIRE` בשתי פקודות נפרדות. בגבול חלון אפשר היה לשלוח **פי 2** מהמותר: לדחוף `max_count` בקצה החלון, ה-counter מתאפס באלפית שנייה לאחר מכן, ולשלוח `max_count` נוספים מיד. בנוסף, אותו אלגוריתם שירת גם auth (anti-bruteforce) וגם chat (API throttle) — שתי דרישות סותרות. |
| **החלטה** | להחליף ב-**שני** Lua scripts אטומיים שונים, מותאמים לאיום: <ul><li>**Auth** (`rate_limit_auth`) → **Sliding-Window Log** (`sliding_window.lua`, sorted-set פר IP). אין burst, חלון מתגלגל אמיתי. תוקף ששתק 10 דקות לא מקבל "קופונים" — כל ניסיון נכנס לחלון הנוכחי בלבד.</li><li>**Chat** (`rate_limit_chat`) → **Token Bucket** (`token_bucket.lua`, hash פר משתמש). Burst עד `capacity` מותר ואף רצוי ל-API; refill חלק (`refill_per_sec`).</li><li>**Rides** (`rate_limit_rides`) → **Sliding-Window Log** (אותו Lua כמו auth, פר משתמש). מקסימום 10 יצירות נסיעה לשעה — anti-abuse על `POST /rides/` ו-`POST /rides/preview-routes`.</li></ul> שני ה-scripts רצים אטומית בתוך Redis, נטענים פעם אחת דרך `register_script` של redis-py (שמטפל אוטומטית ב-`EVALSHA` ו-fallback ל-`EVAL` על `NOSCRIPT` אחרי `SCRIPT FLUSH` או reconnect). |
| **API ל-clients** | החריג `RateLimitExceeded` מועשר ל-`{retry_after, limit, remaining}`, וה-handler המרכזי פולט 4 כותרות סטנדרטיות (Stripe / GitHub convention): `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (epoch seconds), `Retry-After`. בלי זה, ה-client לא יודע מתי לנסות שוב → retry loop אגרסיבי → DDoS עצמי. |
| **אלטרנטיבות שנפסלו** | (1) Token Bucket אחד לשניהם — נחלש מול attacker שמקבץ "קופונים" בעת שקט ואז יורה ב-burst. (2) Leaky bucket — overkill לתרחיש שלנו. (3) `redis.call('TIME')` במקום זמן מהקליינט — דורש `replicate_commands()` ו-non-determinism; זמן מ-EC2 (chrony NTP) מספיק מדויק. (4) wrapper לאחור על `rate_limit_check` — leaky abstraction; עדיף למחוק (יש רק 2 call sites בפרויקט). |
| **Fail-open** | כל `RedisError` או `register_script` שנכשל → `RateLimitResult.fail_open` → הבקשה עוברת. הגנה היא defense-in-depth, ולא כדאי שתפיל login/chat בזמן outage של Redis. נמדד ב-`rate_limit_redis_errors_total{endpoint}`. |
| **Trade-offs (מודעים)** | (1) זמן wall clock מועבר מהקליינט ל-Lua → drift אפשרי בקנה מידה NTP (≪10ms ב-EC2 עם chrony) — מקובל ל-rate limiting. (2) Lua 5.1 לא מבחין int/float; precision של refill תקין לסקאלות שעון אנושיות (שניות-דקות). (3) Sliding-window log שומר entry per request → memory `O(max_count)` לכל מפתח — סביר לעשרות בקשות בחלון. |
| **מטריקות** | `rate_limit_rejected_total{algorithm,endpoint}`, `rate_limit_redis_errors_total{endpoint}`, `rate_limit_evaluation_seconds{algorithm}` (Histogram). |
| **Interview pitch (≈45s)** | *"זיהיתי ש-`INCR+EXPIRE` בשתי פקודות מאפשר 2x burst בגבול החלון. ההחלטה הסניורית הייתה לא רק לתקן עם Lua, אלא להפריד לשני אלגוריתמים: sliding window log ל-auth כי שם burst הוא בדיוק הבעיה (anti-bruteforce), ו-token bucket ל-chat כי שם burst רצוי. שני scripts אטומיים, נטענים פעם אחת דרך register_script של redis-py שמטפל ב-EVALSHA וב-NOSCRIPT אחרי reconnect או SCRIPT FLUSH. ההחזרה היא typed result עם limit/remaining/retry_after_ms שמתורגם ל-X-RateLimit-* headers — זה מה ש-Stripe ו-GitHub עושים, וזה מונע retry storms של clients."* |
| **הפניה** | [`../backend/app/infrastructure/redis/lua/token_bucket.lua`](../backend/app/infrastructure/redis/lua/token_bucket.lua) · [`../backend/app/infrastructure/redis/lua/sliding_window.lua`](../backend/app/infrastructure/redis/lua/sliding_window.lua) · [`../backend/app/infrastructure/rate_limiter.py`](../backend/app/infrastructure/rate_limiter.py) · [`../backend/app/api/dependencies/rate_limit.py`](../backend/app/api/dependencies/rate_limit.py) · [`../backend/app/core/exceptions/handlers.py`](../backend/app/core/exceptions/handlers.py) · ADR §23 |

---

<a id="billing-checkout-db-idempotency-reconciler"></a>

## Billing — אידמפוטנטיות Postgres ל-checkout, reconciler, ומכונת מצבים לתשלום

| | |
|--|--|
| **בעיה** | (1) לחיצה כפולה / retry על **יצירת Checkout Session** יוצרים מספר sessions או חוויית לקוח לא עקבית. Redis-only idempotency (כמו בצ’אט) לא נשמרת בין מחיקות cache / מופעים בלי תכנון נפרד. (2) Webhook מ-Stripe יכול להתעכב או להיעלם — תשלומים נשארים **`pending`** בלי סנכרון. (3) עדכוני סטטוס תשלום חייבים להיות דטרמיניסטיים כדי למנוע “קפיצות” לא חוקיות במסד. |
| **החלטה** | **אידמפוטנטיות DB:** טבלה **`idempotency_keys`** (מפתח פר־משתמש+endpoint, fingerprint, גוף תשובה + status code, TTL). כותרת **`X-Idempotency-Key`** על **`POST /billing/checkout`**. **`IdempotencyMismatchError`** (**422**, `IDEMPOTENCY_MISMATCH`) אם המפתח חוזר עם fingerprint אחר. **Reconciler:** `BillingReconciler` עם **`pg_try_advisory_lock`** (מופע יחיד פעיל), רשימת **`pending`** “מיושנים” (חלון גיל מ־`BILLING_PENDING_*`), **`retrieve_session`** ב-Stripe, החלת **`handle_checkout_completed`** / **`handle_session_expired`**. ניקוי שורות idempotency שפגו. מתוזמן ב־**`app/core/lifespan.py`** (APScheduler; job **`billing_reconciler`**) כש־**`BILLING_RECONCILER_ENABLED`**. **State machine:** `validate_transition` — מעברים מותרים רק מ־`pending` החוצה; מצבי סופיים ריקים (**`PaymentTransitionError`**, **`ILLEGAL_PAYMENT_TRANSITION`**). |
| **אלטרנטיבות** | (1) Redis בלבד ל-checkout — מהיר אבל פחות עמיד למצבי “ברירת מחדל טובים” בתרחיש multi-instance + eviction. (2) ללא reconciler — פשוט יותר; סיכון לתשלומים תקועים. (3) Event-driven reconcile בלבד (SQS/worker נפרד) — כבד לפריסה הנוכחית. |
| **יתרון** | מטמון checkout **עקבי ב-Postgres**; שחזור אחרי תקלות webhook; מדדי **`billing_reconciler_*`** + **`billing_idempotency_hits_total`**; אדמין: **`GET /api/v1/admin/billing/stale-pending`**, **`POST /api/v1/admin/billing/reconcile/{payment_id}`**. |
| **Trade-off** | כתיבות DB נוספות לכל checkout עם מפתח; reconciler מוסיף עומס קריאות Stripe — מוגבל בחלון גיל ובמנעול consultative. המיזוג (**`016_merge015_heads`**) אחרי שני ה־15; מזהה רוויזיה קצר (**`015_billing_idem`**) בשל גבול **`alembic_version.version_num`** (32 תווים). |
| **Interview pitch (≈35s)** | *"ל-billing הפרדתי אידמפוטנטיות מהדפוס של צ’אט: שמרתי תשובת checkout ב-Postgres עם fingerprint, והרצתי reconciler עם advisory lock שמושך מ-Stripe תשלומים pending מיושנים אם ה-webhook איחר. מעל זה מכונת מצבים קשיחה כדי שלא יעברו succeeded חזרה ל-failed בשקט."* |
| **הפניה** | [`../backend/app/domain/billing/idempotency.py`](../backend/app/domain/billing/idempotency.py) · [`../backend/app/domain/billing/reconciler.py`](../backend/app/domain/billing/reconciler.py) · [`../backend/app/domain/billing/state_machine.py`](../backend/app/domain/billing/state_machine.py) · [`../backend/app/domain/billing/router.py`](../backend/app/domain/billing/router.py) · [`../backend/app/core/lifespan.py`](../backend/app/core/lifespan.py) · [`../backend/app/infrastructure/metrics.py`](../backend/app/infrastructure/metrics.py) · [`docs/architecture/API.md`](architecture/API.md) · [`docs/architecture/DATABASE.md`](architecture/DATABASE.md) · [`docs/operations/MONITORING.md`](operations/MONITORING.md) |
| **סיכום ארכיטקטורה בשמירת ניסוח מלא** | [`BILLING_REFACTOR_SUMMARY.md`](BILLING_REFACTOR_SUMMARY.md) — מה היה לפני, מה בנינו, טבלת Kafka, מה מעבר |

---

<a id="audit-log-admin-billing"></a>

## Audit log (admin + billing webhook attempts)

| | |
|--|--|
| **בעיה** | לוגים טקסטואליים בלבד (`[admin_audit]`) לא מספיקים לחקירה אמינה לאורך זמן; בנוסף, ב-billing יש event idempotency (`stripe_event_id`) שמסנן retries ולכן בלי סדר נכון מאבדים תיעוד של ניסיונות כפולים. |
| **החלטה** | טבלת `audit_log` ייעודית (append-only) + repository (`audit_repo.record`). פעולות אדמין רגישות כותבות גם ל-DB וגם ל-logger. ב-`checkout.session.completed` audit attempt נכתב **לפני** בדיקת idempotency כדי לתעד גם duplicate webhook deliveries. |
| **אלטרנטיבות** | (1) להישאר רק עם structured logs. (2) לשלוח audit ל-SIEM חיצוני בלבד. (3) Outbox ייעודי לכל audit event (מורכב יותר כרגע). |
| **יתרון** | forensic trail יציב עם סינון לפי actor/resource/action וזמן; מונע blind spot בסנריו של retries מ-Stripe. |
| **Trade-off** | עוד טבלת write-path בפרודקשן ונפח metadata שדורש משמעת; לכן metadata נשמר קומפקטי ולא payload מלא. |
| **Interview pitch (≈30s)** | *"הוספתי audit persistence לדברים הרגישים באמת, וב-billing הקפדתי לכתוב audit לפני idempotency כדי שגם retries כפולים יהיו traceable. זה ההבדל בין log נוח לבין evidence אמין לחקירה."* |
| **הפניה** | `backend/app/domain/admin/router.py`, `backend/app/domain/billing/service.py`, `backend/app/infrastructure/audit/{model.py,repo.py}`, `backend/alembic/versions/015_add_audit_log.py`, ADR §24 |


---

<a id="h20-google-signin-react-fallback"></a>

## H20 — Google Sign-In: React state fallback + unified timeout detection

| | |
|--|--|
| **בעיה** | `useGoogleSignIn` השתמש ב-55 שורות `createElement`/`appendChild`/`setAttribute` (`buildFallbackButton`) ליצירת כפתור fallback — אנטי-פטרן ב-React app. Triple-nested try/catch נשא מורכבות לא נדרשת. בדיקת timeout נוצרה inline במקום לעבוד עם util הקיים (`isTimeoutOrAbortError`). |
| **החלטה** | (1) מחיקת `buildFallbackButton`; הוספת `const [fallback, setFallback] = useState(false)` ב-hook; כפתור fallback מרונדר כ-React component (`<GoogleFallbackButton />`) ב-`GoogleSignIn.tsx` לפי ה-flag. (2) שטוח של triple try/catch ל-single try/catch. (3) `isTimeoutOrAbortError(err)` מ-`utils/apiError.ts` — אותו util כבר בשימוש ב-`Login.tsx`. (4) `while(firstChild) removeChild` נשאר — Google GIS owns that DOM node, אין חלופה React-ית. |
| **אלטרנטיבות** | (1) Portal-based rendering — overkill כש-fallback הוא inline בתוך אותו container. (2) `dangerouslySetInnerHTML` — מנוגד ל-XSS baseline של הפרויקט. (3) conditional `<script>` inject — legacy pattern, לא testable. |
| **יתרון** | קוד עקבי עם שאר ה-React app; testable, type-safe; XSS-safe; DRY timeout detection. |
| **Trade-off** | Fallback button לא מרונדר ע"י Google SDK — styling ידני שחייב להישאר מסונכרן ויזואלית עם כפתור Google המקורי. |
| **Interview pitch (≈25s)** | *"כפתור fallback של Google Sign-In היה imperative DOM ב-hook (createElement ×55 שורות). העברתי ל-React state + component — zero innerHTML, DRY timeout util, ו-flat error handling. Google עדיין owns את ה-renderButton node, אז ה-removeChild נשאר, אבל כל שאר ה-UI הוא React."* |
| **הפניה** | `frontend/src/components/GoogleSignIn/useGoogleSignIn.ts`, `frontend/src/components/GoogleSignIn/GoogleSignIn.tsx`, `frontend/src/utils/apiError.ts` |

---

<a id="m7-my-bookings-paginated-frontend"></a>

## M7 — `/my-bookings` paginated response: frontend client alignment

| | |
|--|--|
| **בעיה** | בקאנד שונה ל-`PaginatedBookingsResponse` (`{ items, total, page, limit, has_more }`) אבל `fetchMyBookings` בפרונט עדיין ציפה ל-`BookingRow[]` — breaking contract. |
| **החלטה** | `fetchMyBookings` עודכן לקבל `{ page?, limit?, status? }` ולהחזיר `PaginatedBookingsResponse`; ברירות מחדל `page=1, limit=20` תואמות בקאנד. |
| **אלטרנטיבות** | (1) להשאיר unwrap ב-client (`response.data.items`) — חלש, מסתיר את ה-pagination metadata מהצרכן. (2) להחזיר ל-`list[BookingResponse]` בבקאנד — מוותר על pagination. |
| **יתרון** | Contract frontend↔backend מיושר; metadata (total, has_more) זמין ל-UI עתידי. |
| **Trade-off** | צרכנים ישנים (אם היו) צריכים לגשת ל-`.items` — שינוי מינורי. |
| **הפניה** | `frontend/src/api/bookings.ts`, `backend/app/domain/bookings/router.py`, `backend/app/domain/bookings/schema.py`, `docs/architecture/API.md` |
