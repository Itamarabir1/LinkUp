# תוכנית: מסמכי החלטות ארכיטקטוניות (ADR) לראיונות

## עדכונים לפי בקשת המשתמש

- **נתיב יעד:** `docs/adr/` (לא `docs/interview/`).
- **הרחבה:** לנמק במפורש פיצ'רים שנבחרו **לסקייל / עומס / אמינות** (ולמה).
- **FCM:** פרק ייעודי — **למה** מפת `data` בלבד, איך זה משתלב עם Toast/SW, מחזור חיים טוקן, trade-offs מול `notification` payload של Firebase.
- **WebSocket:** פרק ייעודי — **מתי** משתמשים ב-WS בפרויקט, **למה** לא REST/polling בכל מקום, והפרדה בין **chat-ws (Go)** לבין **WS על FastAPI** (נסיעות, מיקום, פיד התראות).

---

## מבנה קבצים לייצור (אחרי אישור ביצוע)

| קובץ | תפקיד |
|------|--------|
| [docs/adr/README.md](docs/adr/README.md) | אינדקס: סדר קריאה, קישורים למקורות אמת (`ARCHITECTURE.md`, `ENGINEERING_HIGHLIGHTS`, `FCM_SYSTEM_SUMMARY`, `REALTIME`) |
| [docs/adr/BACKEND.md](docs/adr/BACKEND.md) | החלטות בקאנד, worker, תשתית, **סקייל** |
| [docs/adr/FRONTEND.md](docs/adr/FRONTEND.md) | החלטות פרונט ווב, real-time בצד לקוח |
| [docs/adr/CHAT_WS.md](docs/adr/CHAT_WS.md) | החלטות שירות Go |
| [docs/adr/FCM_AND_PUSH.md](docs/adr/FCM_AND_PUSH.md) | **אופציונלי מומלץ:** מסמך ממוקד FCM end-to-end (או מקובע כסעיף ארוך ב-`BACKEND.md` + `FRONTEND.md` — לבחור בביצוע) |
| [docs/adr/WEBSOCKETS.md](docs/adr/WEBSOCKETS.md) | **אופציונלי מומלץ:** טבלת "איזה WS / איפה / למה" (או מקובע ב-`BACKEND.md` + `CHAT_WS.md`) |

בביצוע: אם לא רוצים יותר מדי קבצים — לאחד `FCM_AND_PUSH` + `WEBSOCKETS` לתוך `BACKEND.md` / `FRONTEND.md` עם כותרות ברורות.

---

## תוכן מוצע — Backend + סקייל (`BACKEND.md`)

לכל נושא: **הקשר → החלטה → למה זה עוזר בסקייל / בעומס → אלטרנטיבה → משפט לראיון**.

1. **PostgreSQL + PostGIS** — ACID, שאילתות מרחביות; אינדקסים (הפניה ל-`DATABASE.md`).
2. **Connection pool (`DB_POOL_*`) + `pool_pre_ping`** — עומס מקבילי, מניעת חיבורים מתים.
3. **Async SQLAlchemy** — non-blocking I/O; ללא `run_sync` בדומיין (מלבד Alembic).
4. **Pessimistic locking / FOR UPDATE** — מרוצים על אישור/ביטול הזמנה.
5. **Cursor pagination** (נסיעות, צ'אט) מול offset — עומס על טבלאות גדולות.
6. **Redis DB0 vs DB1** — בידוד צ'אט/pub-sub מפני cache ו-broadcast אחר.
7. **RabbitMQ + הפרדת תורים** (notifications / avatar / scheduled) — לא לחסום consumer אחד על השני.
8. **Outbox** — אירועים לא אובדים; API לא תלוי ב-latency של broker.
9. **תזמון:** לולאת publisher קלה (~60s) + משימות כבדות ב-consumer; מרווחי 5 דק / 25 דק / שעה / יום — למה לא cron אחד גדול.
10. **bcrypt ב-thread pool** — לא לחסום event loop תחת הרשמה/לוגין מקבילי.
11. **Rate limiting (Redis)** — הגנה על auth.
12. **JWT ב-WS בלי DB ב-handshake** — חיסכון ב-pool תחת הרבה חיבורי WS (trade-off: `is_active` לא ב-connect).
13. **Structured logging + request id** — תפעול בסקייל.
14. **k6 / עומס** (אופציונלי קצר) — אימות התנהגות תחת עומס.

---

## FCM (`FCM_AND_PUSH.md` או סעיף ב-`BACKEND.md` + `FRONTEND.md`)

מקורות: [docs/FCM_SYSTEM_SUMMARY.md](docs/FCM_SYSTEM_SUMMARY.md), קוד push ב-backend, `frontend/src/services/fcm.ts`, SW.

לכסות:

- **למה data-only מהשרת** — שליטה מלאה על UI; אין התנגשות עם auto-display של `notification` בחזית; אחידות foreground/background.
- **איך המשתמש רואה הודעה** — foreground: Toast + צליל; background: `push` ב-SW.
- **מחזור חיים טוקן** — רישום אחרי login, ניקוי ב-logout לפני ביטול סשן.
- **Trade-offs** — יותר לוגיקה בצד לקוח; תלות ב-VAPID/SW.

---

## WebSocket (`WEBSOCKETS.md` או משולב)

מקורות: [docs/architecture/REALTIME.md](docs/architecture/REALTIME.md), [chat-ws/ARCHITECTURE.md](chat-ws/ARCHITECTURE.md).

טבלה מומלצת (מילוי בביצוע):

| זרימה | שרת | מתי WS | למה לא רק REST/polling |
|--------|-----|--------|-------------------------|
| צ'אט, typing, presence, user events | chat-ws (Go) | עדכונים תכופים, ephemeral | latency, עומס על DB/API |
| סטטוס נסיעה, מיקום נהג/נוסעים | FastAPI + Redis | דחיפה בזמן אמת למספר מנויים | polling היה כבד ואיטי |
| פיד התראות in-app | FastAPI `/notifications/ws` | עדכון מיידי + Redis pub/sub | גיבוי REST בפרונט (poll ארוך) לאחידות חוויה |

להבהיר: **REST** נשאר מקור אמת לרשימות / היסטוריה; **WS** לעדכונים חיים וחוויית "מחובר עכשיו".

---

## Frontend (`FRONTEND.md`)

- Zod על ingress WS — הגנה מפני שדות חסרים תחת עומס/שגיאות שרת.
- Throttle מיקום (~1.5s) — סוללה ועומס שרת.
- פיד התראות: WS + `onOpen` אחרי reconnect + polling גיבוי — אמינות מול רשתות לא יציבות.
- Code splitting / lazy admin — זמן טעינה ראשוני.

---

## chat-ws (`CHAT_WS.md`)

- Go למאות אלפי חיבורים idle-friendly.
- אין לוגיקה עסקית/DB — רק fan-out.
- הפרדה מפורשת מפיד התראות האפליקציה (backend WS).

---

## שלבי ביצוע (אחרי אישור המשתמש)

1. יצירת `docs/adr/README.md`.
2. כתיבת `BACKEND.md` (כולל סעיפי סקייל).
3. כתיבת `FCM_AND_PUSH.md` ו-`WEBSOCKETS.md` (או מיזוג לפי החלטה בזמן ביצוע).
4. כתיבת `FRONTEND.md`, `CHAT_WS.md`.
5. (אופציונלי) שורה ב-[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) או [readme.md](readme.md) עם קישור ל-`docs/adr/`.

---

## Todos

- [ ] `docs/adr/README.md` — אינדקס
- [ ] `docs/adr/BACKEND.md` — כולל סקייל + Outbox + Redis + Rabbit + תזמון
- [ ] `docs/adr/FCM_AND_PUSH.md` — נימוק מלא ל-data-only ומחזור חיים
- [ ] `docs/adr/WEBSOCKETS.md` — מתי WS, איזה שרת, למה
- [ ] `docs/adr/FRONTEND.md`
- [ ] `docs/adr/CHAT_WS.md`
- [ ] קישור מהשורש או מ-`docs/ARCHITECTURE.md` (אופציונלי)
