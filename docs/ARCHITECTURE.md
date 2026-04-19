# ארכיטקטורה — הפניה

תיעוד הארכיטקטורה המלא נמצא בשורש הפרויקט:

**[../ARCHITECTURE.md](../ARCHITECTURE.md)** — סקירת שירותים, תשתית, זרימת תקשורת, דפוסים, ביצועים ואבטחה.

תיעוד מפורט (תיקיית `architecture/`):

- [architecture/DATABASE.md](architecture/DATABASE.md) — מסד נתונים, טבלאות, indexes, migrations
- [architecture/API.md](architecture/API.md) — endpoints, Auth, Pagination, Error responses (קישור ל-ERRORS.md)
- [architecture/EVENTS.md](architecture/EVENTS.md) — Outbox, RabbitMQ, Workers; **Ride: `ride.created` vs `ride.created_for_passengers` (התאמה לנוסעים + מייל)**
- [architecture/REALTIME.md](architecture/REALTIME.md) — WebSocket, Redis Pub/Sub, צ'אט, **user:\*:events**, **ChatMessageSchema** (Zod) + מיפוי ל-MessageResponse; חוזי JSON (נסיעות, מיקום, typing, user events); **התראות in-app** (`/notifications/ws` + פרונט: `useChatNotificationsWebSocket` / `useChatNotificationsFeed`)
- [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md) — סיכום להצגה: פיצ'רים, סקייל, טריקים, real-time, Outbox, **שגיאות API** (סעיף 2ב), **JWT denylist ב-Redis** (סעיף **7ד**), **Idempotency-Key / Redis** (סעיף **7ה**), **Circuit Breaker ל-Google Maps + health `circuit_breakers`** (**Latest architecture updates**, ADR backend **§20**), **סעיף 7ג** (auth בעומס), **סעיף 14** (ריפקטור פרונט), **i18n / לוקאליזציה / טיפוגרפיה ווב**
- [adr/ARCHITECTURE_DECISIONS_FRONTEND.md](adr/ARCHITECTURE_DECISIONS_FRONTEND.md) — סעיפים **10–12**: i18n, פורמט לפי לוקאל, `apiErr` + פונטים ב־CSS Modules
- [FCM_SYSTEM_SUMMARY.md](FCM_SYSTEM_SUMMARY.md) — FCM end-to-end (שרת: מפת `data` בלבד; SW + Toast + צליל בפרונט)
- [../ARCHITECTURE.md](../ARCHITECTURE.md) — סעיף **Email rendering (React Email)**: חוזה `/render`, `EMAIL_RENDERER_URL`, ו-fail-fast registry
- [../backend/app/domain/notifications/config/templates_map/email_conf.py](../backend/app/domain/notifications/config/templates_map/email_conf.py) — מיפוי template keys ל-PascalCase
- [../frontend/src/pages/MyBookings/myBookings.mappers.ts](../frontend/src/pages/MyBookings/myBookings.mappers.ts) — שכבת DTO mappers ל־driver/passenger summary (למניעת cast ישיר של transport objects ב-UI)
- [architecture/DEVELOPMENT.md](architecture/DEVELOPMENT.md) — Setup, env vars (שורש + `backend/.env`), **k6 load test**, מבנה פרויקט
- [ERRORS.md](ERRORS.md) — פורמט שגיאות API, `trace_id`, טבלת `error_code`, Sentry, chat-ws
