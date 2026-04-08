# ארכיטקטורה — הפניה

תיעוד הארכיטקטורה המלא נמצא בשורש הפרויקט:

**[../ARCHITECTURE.md](../ARCHITECTURE.md)** — סקירת שירותים, תשתית, זרימת תקשורת, דפוסים, ביצועים ואבטחה.

תיעוד מפורט (תיקיית `architecture/`):

- [architecture/DATABASE.md](architecture/DATABASE.md) — מסד נתונים, טבלאות, indexes, migrations
- [architecture/API.md](architecture/API.md) — endpoints, Auth, Pagination, Error responses (קישור ל-ERRORS.md)
- [architecture/EVENTS.md](architecture/EVENTS.md) — Outbox, RabbitMQ, Workers
- [architecture/REALTIME.md](architecture/REALTIME.md) — WebSocket, Redis Pub/Sub, צ'אט, **user:\*:events**, **ChatMessageSchema** (Zod) + מיפוי ל-MessageResponse; חוזי JSON (נסיעות, מיקום, typing, user events); **התראות in-app** (`/notifications/ws` + פרונט: `useChatNotificationsWebSocket` / `useChatNotificationsFeed`)
- [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md) — סיכום להצגה: פיצ'רים, סקייל, טריקים, real-time, Outbox, **שגיאות API** (סעיף 2ב), **סעיף 7ג** (auth בעומס), **סעיף 14** (ריפקטור פרונט)
- [FCM_SYSTEM_SUMMARY.md](FCM_SYSTEM_SUMMARY.md) — FCM end-to-end (שרת: מפת `data` בלבד; SW + Toast + צליל בפרונט)
- [architecture/DEVELOPMENT.md](architecture/DEVELOPMENT.md) — Setup, env vars (שורש + `backend/.env`), **k6 load test**, מבנה פרויקט
- [ERRORS.md](ERRORS.md) — פורמט שגיאות API, `trace_id`, טבלת `error_code`, Sentry, chat-ws
