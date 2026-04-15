# תסריט סרטון — ארכיטקטורה (Linkup) · ~6–7 דקות

מטרה: להסביר איך המערכת מפורקת לשירותים, איך נתונים ואירועים זורמים, ואיפה נכנס פיצ’ר הנוסע (חיפוש לעומת שמירת התראה). בסוף יש **קטלוג API** — מקור אמת מפורט: [`architecture/API.md`](architecture/API.md).

---

## חלק א׳ — מה רואים על המסך (0:00–1:00)

**תגיד:**  
“Linkup בנויה משלושה חלקים עיקריים: **בקאנד** ב-Python ו-FastAPI — כל ה-REST, העסקים, ה-DB והאאוטבוקס; **chat-ws** ב-Go — שרת WebSocket לצ’אט והעברת הודעות מ-Redis ללקוחות; ו**פרונט** React עם Vite. הלקוח מדבר ב-HTTP לבקאנד וב-WebSocket ל-chat-ws לפי סוג הפיצ’ר.”

**מומלץ להציג:** דיאגרמה מ־[`README.md`](../../README.md) (mermaid services) או שקופית פשוטה: FE → API, FE → chat-ws, API/worker → Postgres / Redis / RabbitMQ / **email-renderer**.

**תגיד:**  
“יש הפרדה של Redis לוגית: **DB 0** לקאש, rate limit, broadcast של נסיעות; **DB 1** לצ’אט, presence, והשלמת שיחות ל-AI.”

---

## חלק ב׳ — זרימת נתונים ואמינות (1:00–2:30)

**תגיד:**  
“שינויים עסקיים נכתבים ל-PostgreSQL. כשצריך לשלוח מייל, פוש או משימה כבדה — לא סומכים על קריאה סינכרונית לברוקר. משתמשים ב-**Outbox**: באותה טרנזקציה נכתבת שורה ל-`outbox_events`, ו-**outbox-worker** מושך ומפרסם ל-**RabbitMQ**. כך מקבלים משלוח לפחות פעם אחת בלי לחסום את תשובת ה-API.”

**תגיד:**  
“ה-worker מריץ כמה צרכנים: תור התראות — מייל דרך **Brevo + email-renderer (React Email)** ופוש דרך FCM; תור אווטאר ל-S3; תור מתוזמנות — תזכורות, תחזוקה, ועוד. בנוסף הוא מאזין ל-Redis על סיום שיחות להרצת ניתוח AI.”

**מפת מפתחות:** `docs/architecture/EVENTS.md`, `ARCHITECTURE.md` (תרשים Communication Flow).

---

## חלק ג׳ — Real-time: נסיעות, מיקום, צ’אט, התראות באפליקציה (2:30–4:00)

**תגיד:**  
“לצ’אט יש מסלול ייעודי: הודעה נשלחת ב-POST לבקאנד, נשמרת ב-DB, ומפורסמת ל-Redis; chat-ws מנוי על הערוץ ודוחף ל-WebSocket של המשתמשים בשיחה. יש typing, נראות, ו-debounce לעדכון last-seen בבקאנד.”

**תגיד:**  
“מיקום בזמן אמת בנסיעה פעילה עובר ב-REST לבקאנד שמפרסם ל-Redis, והלקוחות מאזינים ב-WebSocket על שרת ה-FastAPI — ערוצים נפרדים לנהג ולנוסעים לפי התיעוד ב-REALTIME.”

**תגיד:**  
“פיד ההתראות במסך ההתראות בווב הוא WebSocket על **הבקאנד** — `/api/v1/notifications/ws` — לא על chat-ws; כך מפרידים בין צ’אט לבין פעמון האפליקציה.”

**מסמכים:** `docs/architecture/REALTIME.md`, `docs/adr/WEBSOCKETS.md`.

---

## חלק ד׳ — פיצ’ר נוסע: חיפוש מול שמירת התראה (4:00–5:15)

**תגיד:**  
“חיפוש נסיעה לנוסע ממומש כ-**GET** ל-`/passenger/passengers/search-rides`. זה שאילתה עם PostGIS ופילטרים — **בלי** ליצור שורה ב-`passenger_requests`. כך אפשר ‘לדפדף’ בחיפוש בלי לזהם את הדאטאבייס.”

**תגיד:**  
“כשהנוסע רוצה להישאר מעודכן, הוא שומר **בקשה** עם `POST /passenger/passengers/` — אותם פרמטרי מסלול, שדה `is_notification_active` שקובע אם לכלול אותו בהתאמות כשנהג יוצר נסיעה, ואופציונלית `group_id` אם החיפוש הוא בהקשר קבוצה.”

**תגיד:**  
“כשנהג יוצר נסיעה, ה-worker מריץ התאמה מול בקשות פעילות — פונקציה כמו `find_passengers_for_ride_notification` — ומסנן בקשות עם התראה כבויה או קבוצה שלא תואמת.”

**החלטה מתועדת:** `docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` — **סעיף 17**.

**פרונט:** `frontend/src/pages/SearchRides/` + `useSearchRides` + `saveSearchAlert` ב-`src/api/passengers.ts`; מצב `hasSearched` כדי להציג ‘אין תוצאות’ רק אחרי חיפוש אמיתי.

---

## חלק ה׳ — אבטחה, סקייל, סגירה (5:15–6:15)

**תגיד בקצרה:**

- JWT access + refresh ב-DB; WebSocket מאמת JWT ב-handshake **בלי** SELECT ל-DB כדי להגן על ה-connection pool.
- bcrypt ב-thread pool; rate limit על auth; שגיאות אחידות עם `error_code` ו-`trace_id` — `docs/ERRORS.md`.
- אדמין: `/api/v1/admin/*` + ממשק React ב-`/admin`.
- פריסה: Docker Compose (כולל `migrate`, `email-renderer`, `outbox-worker`); מניפסטים ל-Kubernetes ב־`k8s/` (כולל `email-renderer`).

---

## חלק ו׳ — קטלוג API (6:15–7:00) — מה להגיד בקצרה

**תגיד:**  
“מפת ה-API המלאה עם כל המסלולים מסודרת בקובץ **docs/architecture/API.md** — Auth, Rides, Passenger, Bookings, Users, Chat, Groups, Geo, Notifications WS, Admin. אני לא קורא הכל בקול; זה מסמך העזר לצוות ולראיונות.”

**Scroll / שקופית:** טבלה אחת מתוך `API.md` (למשל Passenger + Admin) כדי להמחיש עומק.

**Base:** `http://localhost:8000/api/v1` (פרודקשן: לפי `API_PUBLIC_URL`).

### רשימת מרחבי שמות (למילוי מהיר בדיבור)

| Prefix | תוכן עיקרי |
|--------|------------|
| `/auth` | register, login, refresh, logout, אימות מייל, איפוס סיסמה, Google sign-in |
| `/rides` | preview, CRUD נסיעה, start/end/cancel, WS סטטוס ומיקום נוסעים |
| `/passenger/passengers` | בקשות נוסע, חיפוש, בקשה מחיפוש, matches, cancel |
| `/passenger/rides` | פרטי נהג לנסיעה |
| `/bookings` | join, approve/reject, cancel, מניפסט, מיקום נהג/נוסע, WS מיקום |
| `/users` | פרופיל, last-seen, התראות REST, FCM, אווטאר, עדכון פרופיל |
| `/chat` | שיחות, הודעות, read, unread-count, calendar.ics (501) |
| `/groups` | יצירה, הצטרפות, חברים, נסיעות קבוצה, תמונה |
| `/geo` | מפתח מפות, reverse geocode |
| `/notifications` | WS פיד התראות אפליקציה |
| `/admin` | סטטיסטיקות, משתמשים, נסיעות, קבוצות, outbox, lookup |

---

## קבצים להכנה ליד המצלמה

| נושא | קובץ |
|------|------|
| API מלא | `docs/architecture/API.md` |
| סקירת מערכת | `ARCHITECTURE.md`, `README.md` (שורש) |
| אירועים ותורים | `docs/architecture/EVENTS.md` |
| WS ו-GPS | `docs/architecture/REALTIME.md` |
| ADR בקאנד כולל נוסע (סעיף 17) | `docs/adr/ARCHITECTURE_DECISIONS_BACKEND.md` |
| ADR פרונט | `docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` |
| chat-ws מול API | `chat-ws/ARCHITECTURE.md` |
| ארכיטקטורת פרונט | `frontend/docs/ARCHITECTURE.md` |

---

## תזכורת זמן

- 0:00–1:00 שירותים ו-Redis
- 1:00–2:30 Outbox + RabbitMQ + worker
- 2:30–4:00 real-time (צ’אט, מיקום, התראות)
- 4:00–5:15 נוסע: חיפוש מול POST
- 5:15–6:15 אבטחה וסקייל
- 6:15–7:00 קטלוג API + הפניה ל-API.md

---

## הרחבה לסרטון ארוך יותר (10+ דקות)

אם הסרטון מתארך, אפשר **לשלב בלוקים נוספים** (אחרי החלקים הקיימים או במקום קיצור שלהם). סדר מוצע וזמנים משוערים:

| חלק משוער | נושא | מה להגיד / להציג |
|-----------|------|-------------------|
| +1:00–2:00 | **מסד נתונים** | PostgreSQL + **PostGIS** — איפה נכנס הגיאו; טבלאות ליבה (`rides`, `bookings`, `passenger_requests`, `outbox_events`, …); למה אינדקסים חשובים לחיפוש ולהזמנות. מקור: `docs/architecture/DATABASE.md`. |
| +0:45–1:15 | **מיגרציות וסכימה** | Alembic כמקור שינויי סכימה; שירות **`migrate`** ב-Docker Compose לפני עליית ה-API; `db/schema.sql` כעזר. |
| +1:00–1:45 | **פריסה מקומית מול K8s** | Compose: **db**, **redis**, **rabbitmq**, **`migrate`** (Job לפני API), **`email-renderer`**, **backend**, **outbox-worker**, **chat-ws**; `depends_on` + healthchecks; `UVICORN_WORKERS`. אז מעבר קצר ל־`k8s/` — מפת שירותים (כולל `k8s/email-renderer`), בלי לעבור כל מניפסט. |
| +0:45–1:00 | **CI/CD** | **ארבעה** workflows ב־`.github/workflows/`: `backend-ci`, `frontend-ci`, `chat-ws-ci`, **`email-renderer-ci`** — lint/tests/build; ב־`main` דחיפת תמונות ל־GHCR (frontend ו־email-renderer). |
| +1:15–2:00 | **chat-ws לעומק** | למה **Go** ל-WS; `PSubscribe` ל-Redis; אין DB בשרת — רק forward; JWT; `presence` + debounce; קריאת `last_seen` מ-REST הבקאנד. `chat-ws/ARCHITECTURE.md`, `docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md`. |
| +1:00–1:30 | **ערוצי התראות** | הפרדה: צ’אט (`chat:notification:*` דרך chat-ws) מול פיד האפליקציה (`/api/v1/notifications/ws` על FastAPI); Outbox → RabbitMQ → **Brevo** / **FCM**; **למה FCM רק מפת `data`** — `docs/FCM_SYSTEM_SUMMARY.md`, `docs/adr/FCM_AND_PUSH.md`. |
| +0:45–1:00 | **אבטחה מפורטת** | rate limit על auth; **מניעת user enumeration** בלוגין; `get_current_user_ws` בלי DB ב-connect — trade-off. |
| +0:45–1:00 | **איכות ועומס** | pytest בבקאנד; Vitest בפרונט; **k6** — מה בודקים (auth, זרימות ליבה), בלי להריץ live בסרטון. `backend/k6/scripts/`, `docs/ENGINEERING_HIGHLIGHTS.md`. |
| +0:45–1:15 | **מדיה** | presigned upload לאווטאר/קבוצות; worker לעיבוד תמונה; **CloudFront** אופציונלי מול presigned GET. |
| +1:00–1:45 | **דומיין לדוגמה (בחר אחד)** | **קבוצות:** קוד הזמנה, `flush` + retry על `IntegrityError`. **או** **תזמון:** `scheduled_notifications` במקום דגלים ישנים על ride/booking — `ReminderScheduler`. |

**תזכורת זמן משולבת (בסיס 7 דק׳ + הרחבה):** עם כל הבלוקים למעלה הסרטון יכול בקלות להגיע ל־**12–18 דקות** — כדאי לבחור 4–6 נושאים שמתאימים לקהל (למשל DB + chat-ws + התראות + CI).

### קבצים נוספים להרחבה

| נושא | קובץ |
|------|------|
| DB | `docs/architecture/DATABASE.md` |
| FCM | `docs/FCM_SYSTEM_SUMMARY.md`, `docs/adr/FCM_AND_PUSH.md` |
| chat-ws ADR | `docs/adr/ARCHITECTURE_DECISIONS_CHAT_WS.md` |
| הדגשים כלליים | `docs/ENGINEERING_HIGHLIGHTS.md` |
| שגיאות | `docs/ERRORS.md` |
| אדמין | `ADMIN_DASHBOARD.md` (בשורש) |
| Kubernetes (סדר פריסה) | `k8s/README.md` |
