# החלטות ארכיטקטוניות — chat-ws (Go)

מסמך להצגה בראיון על שירות ה-WebSocket לצ'אט. פירוט גבולות: [../../chat-ws/ARCHITECTURE.md](../../chat-ws/ARCHITECTURE.md).

---

## 1. למה Go ולא Python WebSocket

| | |
|--|--|
| **הקשר** | אלפי חיבורי WS ארוכים, הודעות קצרות ותכופות (צ'אט, typing, presence). |
| **החלטה** | שירות נפרד ב-**Go** — goroutines ועלות נמוכה לחיבור בהשוואה לסטאק Python כבד יותר לכל חיבור. |
| **למה** | מפורש ב-[README.md](../../README.md) (סעיף **Architecture Decisions**): שרתי WebSocket נהנים מ-overhead נמוך לחיבור וקונקרנציה גבוהה; השירות **לא עושה DB ולא לוגיקה עסקית** — רק subscribe ל-Redis ודחיפה ללקוחות. |
| **אלטרנטיבה** | WS בתוך FastAPI — אפשרי לזרימות מצומצמות, אבל עומס חיבורים וזיכרון היו מסבכים את נתיב ה-API. |
| **בקצרה לראיון** | "הפרדנו את צ'אט ה-WS ל-Go כדי לטפל בהרבה חיבורים idle בלי למשוך את כל סטאק הפייתון לנתיב ה-real-time." |

---

## 2. גבול אחריות — chat-ws מול backend

| chat-ws **כן** | chat-ws **לא** |
|----------------|-----------------|
| ניהול חיבורי WebSocket, אימות JWT על WS ו-HTTP מינימלי | Calendar export, ייצוא iCal |
| Subscribe ל-Redis (`chat:conversation:*`, `chat:typing:*`, `user:*:events`, presence online/offline) | לוגיקה עסקית, שאילתות DB |
| Forward הודעות ללקוחות; typing; `user_online` / `user_offline` | ניתוח AI — רק forward אם צריך; התוצאה נשמרת ב-backend + worker |
| Presence ב-Redis (`presence:*`), debounce לעדכון last-seen | CRUD צ'אט — נשמר ב-**POST** ל-FastAPI, שאז מפרסם ל-Redis |

**בקצרה לראיון:** "chat-ws הוא שכבת fan-out: Redis → לקוח. כל מה שדורש DB או כללים עסקיים נשאר ב-Python."

---

## 3. JWT זהה ל-backend

| | |
|--|--|
| **החלטה** | אותו **SECRET_KEY** (או מפתח חתימה מוסכם) כמו ב-FastAPI — טוקן שמונפק ב-login תקף גם ל-`ws://…/ws?token=…`. |
| **למה** | מנגנון auth אחיד; אין מערכת session נפרדת ל-WS. |
| **בקצרה לראיון** | "אותו JWT — הלקוח לא מנהל זהות כפולה בין API לצ'אט." |

---

## 4. Redis DB1 בלבד

| | |
|--|--|
| **החלטה** | chat-ws מתחבר רק ל-**Redis logical DB 1** — אותו namespace שבו ה-backend מפרסם pub/sub לצ’אט, **`user:{id}:events`**, presence, ויכול בתיאוריה לכלול **`chat:completion:*`** אם מתווסף publisher (כרגע יש מאזין ב־Python; פרסום מ-backend לא אומת) — ראו [`architecture/AI.md`](../architecture/AI.md). |
| **למה** | עקביות עם [publisher ב-Python](../../backend/app/infrastructure/redis/); DB0 נשאר ל-cache ו-rate limit בלי להתנגש בערוצי צ'אט. |
| **בקצרה לראיון** | "DB1 משותף בכוונה ל-backend — אחרת היינו צריכים תיאום מפתחות בין שני מקורות אמת." |

---

## 5. HTTP מינימלי — presence ו-last-seen

| | |
|--|--|
| **החלטה** | למשל **`GET /presence/{user_id}`** — `online` מ-Redis; **`last_seen`** נמשך מ-backend (`GET /api/v1/users/{id}/last-seen`) כשצריך. עדכוני last-seen debounced דרך מפתחות Redis + PATCH ל-backend לפי המדיניות ב-[REALTIME.md](../architecture/REALTIME.md). |
| **למה דרך chat-ws לחלק מהזרימה** | הלקוח כבר מחובר לשירות שמבין presence; מרכזים heartbeat/debounce קרוב ל-WS בלי לעקוף את אותו process בכל ping. |
| **למה לא הכל ב-chat-ws** | מקור האמת ל-`last_seen` ב-DB נשאר ב-backend — Single source of truth. |
| **בקצרה לראיון** | "HTTP קטן ליד ה-WS: online בזמן אמת מ-Redis, אמת היסטורית מה-API." |

---

## 6. פיד התראות in-app — REST + אירועי `user:{id}:events` על chat-ws

| | |
|--|--|
| **הערה** | הרשימה נטענת מ-**`GET /api/v1/users/me/notifications`** (polling ~5 דקות ב־`useChatNotificationsFeed`). דחיפת רענון UI מגיעה דרך **`user:{user_id}:events`** על **אותו חיבור chat-ws** (לא FastAPI WS נפרד — ראו [WEBSOCKETS.md](WEBSOCKETS.md), [REALTIME.md](../architecture/REALTIME.md)). |
| **למה** | חיבור WS אחד למשתמש; פרסום מ־`WebSocketProvider` ב-backend ל-Redis המשותף עם chat-ws. |

---

## 7. פריימים נכנסים — גודל מקסימלי ו־rate limiting לטייפינג

| | |
|--|--|
| **בעיה** | ללא `SetReadLimit`, לקוח יכול לשלוח מסרים WebSocket גדולים מאוד ולהעמיס זיכרון/CPU על `json.Unmarshal`; ללא מגבלה על פרסום typing, מתקף יכול לייצר אלפי `PublishTyping` לשנייה ל־Redis. |
| **החלטה** | אחרי **`Upgrade`**: **`conn.SetReadLimit(int64(maxMessageSize))`** עם **`maxMessageSize = 2048`** בתוך החבילה `hub` (מספיק לפלטפת JSON של typing + UUIDs לפי הגבלות שם בסכימת משתמש). **Limiter נפרד לכל חיבור** דרך **`golang.org/x/time/rate`**: **`NewLimiter(rate.Limit(30), 60)`** — רק נתיבים שמפרסמים **`typing_start`/`typing_stop`** בודקים **`Allow()`** לפני `Marshal`/`PublishTyping`. **`ping`** נשאר מחוץ ללימיטר. בעת חריגה מקצב הטייפינג — **drop שקט** (אין סגירת WS, אין תגובת שגיאה לפריים). |
| **Trade-off** | פרסומות typing בשיא קיצוני עשויות להישמט; גודל 2048 בייט משאיר פריים typing לגיטימיים מתחת הגג. |
| **בקצרה לראיון** | "ב־hub הוגבל גודל מסר מהלקוח, ומהדקתי פרסום typing לרדיס פר־חיבור — בלי לפגוע ב-ping של presence." |
| **קוד** | [`handler.go`](../../chat-ws/internal/hub/handler.go), [`conn.go`](../../chat-ws/internal/hub/conn.go) |

---

## 8. הקשחה תפעולית — `/healthz`, graceful shutdown, read deadline, panic recovery, sync.Once teardown (H7–H11)

| | |
|--|--|
| **בעיה** | (H7) אין endpoint `/healthz` — docker-compose healthcheck מחזיר 404; chat-ws יכול להיראות חי בזמן שה-subscribers מתים. (H8) `http.ListenAndServe` בלי `Shutdown` — SIGTERM הורג חיבורים WS מיידית. (H9) אין `SetReadDeadline`/`SetPongHandler` — לקוחות מתים מחזיקים goroutines לנצח. (H10) אין `recover()` — panic בגורוטינה אחת מפיל את כל התהליך. (H11) `close(c.done)` נקרא ישירות — מרוץ בין handler defer לבין hub broadcast timeout יכול לסגור את הערוץ פעמיים → panic. |
| **החלטה** | **H7:** `/healthz` בודק Redis PING + `Hub.SubscribersHealthy()` — שלוש `atomic.Int64` timestamps (chat/offline/online), מעודכנות ב-`(P)Subscribe` מוצלח, threshold 2 דקות; seeded ל-`now` ב-`NewHub` (grace window). **H8:** `*http.Server` + `srv.Shutdown(10s)` אחרי `cancel()`. **H9:** `conn.SetReadDeadline(pongWait)` + `SetPongHandler` לפני read loop. **H10:** `internal/safego/safego.go` עם `RecoverPanic(component, op)` — `defer` בכל goroutine עצמאית. **H11:** `Conn` struct מקבל `closeOnce sync.Once`; `Conn.Close()` עוטף `close(c.done)` ב-`sync.Once`; `Conn.Done()` חושף `<-chan struct{}` read-only — כל call site (handler, hub, write pump) משתמש ב-methods בלבד, double-close בלתי אפשרי מבנית. |
| **אלטרנטיבות** | (H7) Redis PING בלבד — לא תופס subscriber מת. (H10) inline `recover()` בכל פונקציה — code duplication. (H11) `select` עם `default` לפני close — אינו מונע מרוצים, רק מסתיר panic; `recover()` סביב close — מסתיר באגים אמיתיים. |
| **יתרון** | docker-compose healthcheck עובד באמת; deploy graceful; אין דליפת goroutines; panic לא הורג תהליך; teardown בטוח מבנית ללא תלות בתזמון. |
| **Trade-off** | H7 subscriber liveness תלוי בהצלחת subscribe, לא בקבלת הודעה (שתיקה לגיטימית לא נתפסת); H10 recovery בולע את ה-panic — ה-goroutine נעצרת בשקט (מתועד בלוג). H11 מוסיף שדה אחד ל-struct ו-indirection קלה — עלות זניחה מול בטיחות. |
| **בקצרה לראיון** | "הוספתי healthz שבודק לא רק Redis PING אלא גם שכל subscriber goroutine באמת subscribed — עם atomic timestamps. Graceful shutdown, read deadline לזיהוי לקוחות מתים, panic recovery שמשותף ב-internal/safego, ו-sync.Once על close(done) כדי שמרוצים בין handler ל-hub לא יגרמו panic." |
| **קוד** | [`cmd/server/main.go`](../../chat-ws/cmd/server/main.go), [`internal/hub/hub.go`](../../chat-ws/internal/hub/hub.go), [`internal/hub/handler.go`](../../chat-ws/internal/hub/handler.go), [`internal/hub/conn.go`](../../chat-ws/internal/hub/conn.go), [`internal/safego/safego.go`](../../chat-ws/internal/safego/safego.go), [`internal/redis/subscriber.go`](../../chat-ws/internal/redis/subscriber.go) |

---

## 9. Per-frame WebSocket writes (C1 — audit fix)

| | |
|--|--|
| **בעיה** | `RunWritePump` השתמש בדפוס gorilla chat example: drain ה-`Send` channel, שרשור כל ההודעות עם `\n` ל-`NextWriter` אחד, וסגירת writer — מספר אובייקטי JSON ב-frame יחיד. הפרונט פיצל לפני parse, אבל כל consumer חיצוני (mobile, CLI, tests) חייב היה לדעת על הקונבנציה הלא-סטנדרטית. |
| **החלטה** | `RunWritePump` שולח כל הודעה כ-frame עצמאי: `c.Conn.WriteMessage(websocket.TextMessage, message)`. Drain optimization נשאר (לולאה על `len(c.Send)` אחרי ההודעה הראשונה), אבל כל פריט → frame נפרד. |
| **אלטרנטיבות** | (1) JSON-Lines רשמי (NDJSON) — עדיין דורש parser מיוחד. (2) Frame batching with length prefix — over-engineering לצ'אט. |
| **יתרון** | כל frame הוא JSON תקני; consumers פשוטים (`JSON.parse(event.data)` בלי split); תואם ל-WebSocket spec (הודעות עצמאיות). |
| **Trade-off** | יותר syscalls/frames כשיש burst (במקום frame אחד עם 3 הודעות, יש 3 frames); בפועל ה-overhead זניח ב-TCP_NODELAY + buffer בדפדפן. |
| **בקצרה לראיון** | "תיקנתי את write pump מ-batch-to-one-frame ל-frame-per-message — הפרונט כבר לא צריך לפצל, וכל consumer חיצוני מקבל JSON תקני." |
| **קוד** | [`conn.go`](../../chat-ws/internal/hub/conn.go) |

---

## קישורים

- [../../README.md](../../README.md) — Architecture Decisions  
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) — סקירה כללית  
- [../architecture/REALTIME.md](../architecture/REALTIME.md)
