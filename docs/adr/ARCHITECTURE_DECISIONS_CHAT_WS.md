# החלטות ארכיטקטוניות — chat-ws (Go)

מסמך להצגה בראיון על שירות ה-WebSocket לצ'אט. פירוט גבולות: [../../chat-ws/ARCHITECTURE.md](../../chat-ws/ARCHITECTURE.md).

---

## 1. למה Go ולא Python WebSocket

| | |
|--|--|
| **הקשר** | אלפי חיבורי WS ארוכים, הודעות קצרות ותכופות (צ'אט, typing, presence). |
| **החלטה** | שירות נפרד ב-**Go** — goroutines ועלות נמוכה לחיבור בהשוואה לסטאק Python כבד יותר לכל חיבור. |
| **למה** | מפורש ב-[readme.md](../../readme.md) (סעיף **Architecture Decisions**): שרתי WebSocket נהנים מ-overhead נמוך לחיבור וקונקרנציה גבוהה; השירות **לא עושה DB ולא לוגיקה עסקית** — רק subscribe ל-Redis ודחיפה ללקוחות. |
| **אלטרנטיבה** | WS בתוך FastAPI — אפשרי לזרימות מצומצמות, אבל עומס חיבורים וזיכרון היו מסבכים את נתיב ה-API. |
| **בקצרה לראיון** | "הפרדנו את צ'אט ה-WS ל-Go כדי לטפל בהרבה חיבורים idle בלי למשוך את כל סטאק הפייתון לנתיב ה-real-time." |

---

## 2. גבול אחריות — chat-ws מול backend

| chat-ws **כן** | chat-ws **לא** |
|----------------|-----------------|
| ניהול חיבורי WebSocket, אימות JWT על WS ו-HTTP מינימלי | Calendar export, ייצוא iCal |
| Subscribe ל-Redis (`chat:conversation:*`, `chat:typing:*`, `chat:notification:*`, `user:*:events`, presence online/offline) | לוגיקה עסקית, שאילתות DB |
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
| **החלטה** | chat-ws מתחבר רק ל-**Redis logical DB 1** — אותו namespace שבו ה-backend מפרסם pub/sub לצ'אט, completion, `user:{id}:events`, presence. |
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

## 6. פיד התראות האפליקציה — לא ב-chat-ws

| | |
|--|--|
| **הערה** | מסך הפעמון / רשימת התראות in-app בווב מתחבר ל-**`/api/v1/notifications/ws`** ב-FastAPI, לא ל-chat-ws (ראו [WEBSOCKETS.md](WEBSOCKETS.md)). |
| **למה** | הפרדת מחזור חיים: ערוצי צ'אט מול ערוץ per-user להתראות אפליקציה; אותו דפוס אימות ו-Redis פנימי כמו WS אחרים ב-backend. |

---

## קישורים

- [../../readme.md](../../readme.md) — Architecture Decisions  
- [../../ARCHITECTURE.md](../../ARCHITECTURE.md) — סקירה כללית  
- [../architecture/REALTIME.md](../architecture/REALTIME.md)
