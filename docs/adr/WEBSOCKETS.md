# מתי משתמשים ב-WebSocket ולמה

מסמך לראיון: **איפה** ב-Linkup יש WS, **איזה שרת** משרת אותו, ו**למה** לא הסתפקנו ב-REST או ב-polling בלבד.

---

## עקרון כללי

| כלי | מתאים כש… |
|-----|-----------|
| **REST** | פעולות request/response, מקור אמת לרשימות, כתיבה ל-DB, עסקאות. |
| **WebSocket** | עדכונים **שכיחים** או **דחופים** לכמה מנויים, כשה-latency של polling גבוה מדי או כשהעומס על השרת/DB היה גדול. |
| **Polling (REST חוזר)** | גיבוי כשה-WS נופל, או כשהתדירות נמוכה מספיק (למשל כל כמה דקות). |

ב-Linkup **REST נשאר מקור האמת** לנתונים; WS משמש ל**דחיפה** של שינויים וחוויית "חי".

---

## טבלת WebSocket בפרויקט

| זרימה | שרת | נתיב / חיבור | מתי נכנסים ל-WS | למה לא רק polling |
|--------|-----|----------------|------------------|-------------------|
| **צ'אט** — הודעות, typing, presence, `user_online` / `user_offline`, אירועי דומיין `user:{id}:events` | **chat-ws (Go)** | `ws://…/ws?token=JWT` (ב-dev לעיתים ישיר ל-8081) | משתמש בשיחה / רשימת הודעות שצריכה חיוּת | הודעות ו-typing הם אירועים תכופים; polling היה הורס latency ו-DB. |
| **סטטוס נסיעה** (למשל התחל/סיים נסיעה) | **FastAPI** | `/api/v1/rides/ws/{ride_id}?token=JWT` | מסכים שמציגים נסיעה פעילה / רשימה דינמית | עדכון מיידי לכל המחוברים לערוץ Redis `ride_{id}`. |
| **מיקום נהג → נוסעים** | **FastAPI** | `/api/v1/bookings/ws/{booking_id}/location?token=JWT` | נסיעה active, נוסע מאושר | דיווחי מיקום תכופים; WS מפיץ מ-Redis בלי לקרוא DB לכל שידור. |
| **מיקום נוסעים → נהג** | **FastAPI** | `/api/v1/rides/ws/{ride_id}/passengers?token=JWT` | נהג בנסיעה active | אותו עיקרון — ערוץ נפרד ממיקום הנהג. |
| **פיד התראות in-app** (רשימת התראות / סנכרון UI) | **FastAPI** | `/api/v1/notifications/ws?token=JWT` | משתמש מחובר באפליקציית הווב | Redis Pub/Sub פנימי ל-`user_{id}`; עדכון מיידי כשמגיעה התראה. |

---

## שני סוגי שרתי WebSocket — למה שניים?

### chat-ws (Go)

- **מטרה:** הרבה חיבורים **ארוכים** יחסית, הרבה הודעות קצרות (typing, presence), fan-out מ-Redis **בלי** לוגיקה עסקית בנתיב הקריטי.
- **למה לא אותו process כמו FastAPI לצ'אט:** עומס חיבורים וזיכרון; Go עם goroutines מתאים למודל הזה (ראו [ARCHITECTURE_DECISIONS_CHAT_WS.md](ARCHITECTURE_DECISIONS_CHAT_WS.md)).

### FastAPI WebSocket

- **מטרה:** WS שצמוד לדומיין ה-API (נסיעות, הזמנות, התראות) ולכבר קיים **אותו Redis publisher** מה-backend (למשל `publish_ride_event`, notification streamer).
- **למה לא לדחוף הכל ל-Go:** פחות כפילות לוגיקת authz דרך שירות שכבר מכיר את הדומיין; חלק מהזרימות פשוטות יותר להשאיר ב-Python לצד ה-REST.

---

## התראות in-app: WS + גיבוי REST

| | |
|--|--|
| **ראשי** | `useChatNotificationsWebSocket` על גבי `useReconnectingWebSocket`; ב-`onOpen` (כולל אחרי reconnect) — רענון פיד, unread, אירוע `linkup-notifications-refresh`. |
| **גיבוי** | polling ל-REST כל ~**5 דקות** (`useChatNotificationsFeed`) כשה-WS לא זמין או רשת לא יציבה. |
| **למה** | אמינות מול ניתוקים בלי לרדוף אחרי השרת כל שנייה. |

---

## אימות ב-WS

- **chat-ws ו-FastAPI WS:** JWT ב-query (או מנגנון מוסכם); ב-FastAPI חלק מה-handshakes **ללא DB** — ראו [ARCHITECTURE_DECISIONS_BACKEND.md](ARCHITECTURE_DECISIONS_BACKEND.md) סעיף 12.

---

## קישורים

- [../architecture/REALTIME.md](../architecture/REALTIME.md)  
- [../../chat-ws/ARCHITECTURE.md](../../chat-ws/ARCHITECTURE.md)  
- [README.md](README.md)
