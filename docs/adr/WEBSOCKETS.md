# מתי משתמשים ב-WebSocket ולמה

מסמך לראיון: **איפה** ב-LinkUp יש WS, **איזה שרת** משרת אותו, ו**למה** לא הסתפקנו ב-REST או ב-polling בלבד.

---

## עקרון כללי

| כלי | מתאים כש… |
|-----|-----------|
| **REST** | פעולות request/response, מקור אמת לרשימות, כתיבה ל-DB, עסקאות. |
| **WebSocket** | עדכונים **שכיחים** או **דחופים** לכמה מנויים, כשה-latency של polling גבוה מדי או כשהעומס על השרת/DB היה גדול. |
| **Polling (REST חוזר)** | גיבוי כשה-WS נופל, או כשהתדירות נמוכה מספיק (למשל כל כמה דקות). |

ב-LinkUp **REST נשאר מקור האמת** לנתונים; WS משמש ל**דחיפה** של שינויים וחוויית "חי".

---

## טבלת WebSocket בפרויקט

| זרימה | שרת | נתיב / חיבור | מתי נכנסים ל-WS | למה לא רק polling |
|--------|-----|----------------|------------------|-------------------|
| **צ'אט** — הודעות, typing, presence, `user_online` / `user_offline`, אירועי דומיין `user:{id}:events` | **chat-ws (Go)** | `ws://…/ws?token=JWT` (ב-dev לעיתים ישיר ל-8081) | משתמש בשיחה / רשימת הודעות שצריכה חיוּת | הודעות ו-typing הם אירועים תכופים; polling היה הורס latency ו-DB. |
| **סטטוס נסיעה** (למשל התחל/סיים נסיעה) | **FastAPI** | `/api/v1/rides/ws/{ride_id}?token=JWT` | מסכים שמציגים נסיעה פעילה / רשימה דינמית | עדכון מיידי לכל המחוברים לערוץ Redis `ride_{id}`. |
| **מיקום נהג → נוסעים** | **FastAPI** | `/api/v1/bookings/ws/{booking_id}/location?token=JWT` | נסיעה active, נוסע מאושר | דיווחי מיקום תכופים; WS מפיץ מ-Redis בלי לקרוא DB לכל שידור. |
| **מיקום נוסעים → נהג** | **FastAPI** | `/api/v1/rides/ws/{ride_id}/passengers?token=JWT` | נהג בנסיעה active | אותו עיקרון — ערוץ נפרד ממיקום הנהג. |
| **התראות in-app** (רשימה + רענון UI) | **REST + chat-ws** | רשימה: **`GET /api/v1/users/me/notifications`**; דחיפת רענון: **`user:{id}:events`** על חיבור **`ws://…/ws`** (chat-ws), לא FastAPI נפרד | משתמש מחובר בווב | הרשימה נמשכת ב-REST (וגיבוי polling ~5 דקות); עדכון מיידי דרך אותו Redis Pub/Sub כמו אירועי דומיין בצ’אט — ראו [`REALTIME.md`](../architecture/REALTIME.md). |

---

## שני סוגי שרתי WebSocket — למה שניים?

### chat-ws (Go)

- **מטרה:** הרבה חיבורים **ארוכים** יחסית, הרבה הודעות קצרות (typing, presence), fan-out מ-Redis **בלי** לוגיקה עסקית בנתיב הקריטי.
- **למה לא אותו process כמו FastAPI לצ'אט:** עומס חיבורים וזיכרון; Go עם goroutines מתאים למודל הזה (ראו [ARCHITECTURE_DECISIONS_CHAT_WS.md](ARCHITECTURE_DECISIONS_CHAT_WS.md)).

### FastAPI WebSocket

- **מטרה:** WS שצמוד לדומיין ה-API (נסיעות, הזמנות) עם **אותו Redis publisher** מה-backend (למשל `publish_ride_event`). התראות in-app ברמת רשימה נשענות על REST; דחיפת רענון UI דרך chat-ws (`user:{id}:events`) — ראו למעלה.
- **למה לא לדחוף הכל ל-Go:** פחות כפילות לוגיקת authz דרך שירות שכבר מכיר את הדומיין; חלק מהזרימות פשוטות יותר להשאיר ב-Python לצד ה-REST.

---

## התראות in-app: REST + אירועי `user:*:events` על chat-ws

| | |
|--|--|
| **מקור הרשימה** | **`GET /api/v1/users/me/notifications`** — React Query ב־`useChatNotificationsFeed`, כולל **polling** כל ~**5 דקות** כגיבוי כשאין עדכון חי. |
| **רענון חי** | אין WS ייעודי ל־`/api/v1/notifications/ws` ב-FastAPI כרגע. עדכוני UI מגיעים דרך **chat-ws**: פריים על **`user:{id}:events`** (`useUserEventStream` / `useUserEvent` ב־`ChatContext`) אחרי פרסום מ־`WebSocketProvider` ב-backend. |
| **למה** | חיבור WS אחד לצ’אט + אירועי דומיין; REST נשאר מקור האמת לרשימה. |

---

<a id="frontend-ws-reconnect-doc"></a>

## Reconnect (פרונט) — exponential backoff + jitter

בין ניסיונות חיבור מחדש (**chat-ws:** [`useChatWebSocket`](../../frontend/src/pages/MessageThread/useChatWebSocket.ts), [`useUserEventStream`](../../frontend/src/hooks/useUserEventStream.ts) שעוטף [`useReconnectingWebSocket`](../../frontend/src/hooks/useReconnectingWebSocket.ts); **FastAPI rides:** [`useRideWebSocket`](../../frontend/src/hooks/useRideWebSocket.ts) → אותו `useReconnectingWebSocket`; **GPS:** [`useReconnectingWebSocketState`](../../frontend/src/hooks/useReconnectingWebSocketState.ts)) הפרונט משתמש ב־**[`computeReconnectDelayMs`](../../frontend/src/utils/reconnectBackoff.ts)** ב־[`reconnectBackoff.ts`](../../frontend/src/utils/reconnectBackoff.ts): **מעריכה + ±20% jitter** (בסיס **3s**, תקרה **30s**); מונה ניסיונות **פר־`useEffect`**, **מתאפס ב־`onopen`**. **למה:** outage כללי (chat-ws / FastAPI / רשת) — מצמצמים **thundering herd** ברגע ה-recovery. פירוט: [`architecture/REALTIME.md`](../architecture/REALTIME.md), [`FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff`](../FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff).

---

## אימות ב-WS

- **chat-ws ו-FastAPI WS:** JWT ב-query (או מנגנון מוסכם); ב-FastAPI חלק מה-handshakes **ללא DB** — ראו [ARCHITECTURE_DECISIONS_BACKEND.md](ARCHITECTURE_DECISIONS_BACKEND.md) סעיף 12.

---

## קישורים

- [../architecture/REALTIME.md](../architecture/REALTIME.md)  
- [../../chat-ws/ARCHITECTURE.md](../../chat-ws/ARCHITECTURE.md)  
- [README.md](README.md)
