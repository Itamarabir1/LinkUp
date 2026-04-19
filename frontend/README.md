# LinkUp Frontend (React + Vite)

אפליקציית ווב ב-React + TypeScript (Vite) ל-LinkUp: ניהול נסיעות, קבוצות, צ'אט בזמן אמת, התחברות עם Google ואימייל/סיסמה, תמונות פרופיל (S3), **תמיכה ב-RTL ובאנגלית (i18next)** עם מעבר שפה, ופורמט תאריכים לפי לוקאל.

> **הערה:** ריצת Frontend CI ב-GitHub מופעלת רק כשקומיט משנה קבצים תחת `frontend/`.

---

## דרישות

- Node.js 18+
- npm (או pnpm / yarn אם מעדיפים)
- Backend רץ (ברירת מחדל: `http://127.0.0.1:8000`)


---

## התקנה והרצה בפיתוח

```bash
cd frontend
npm install
npm run dev
```

ברירת המחדל של Vite היא `http://localhost:5173`.  
הבקשות ל-API עוברות דרך proxy של Vite אל ה-backend (ללא בעיות CORS) כאשר עובדים ב-dev.

---

## משתני סביבה (`frontend/.env`)

יש קובץ `frontend/.env.example` עם ברירות מחדל. כדי להתחיל:

```bash
cp frontend/.env.example frontend/.env
# ערוך את frontend/.env לפי הצורך
```

המשתנים העיקריים:

- **REST API** – תמיד נתיב יחסי `/api/v1` (אותו host; Vite proxy בפיתוח ל־`localhost:8000`, Nginx בפרודקשן).
- **צ'אט WebSocket** – ב־[`src/config/env.ts`](src/config/env.ts) פונקציה `getChatWebSocketUrl`: ב־**DEV** (`import.meta.env.DEV`) חיבור **ישיר** ל־`ws://localhost:8081/ws?token=…` (שירות `chat-ws` בדוקר מפרסם 8081 ל־host). ב־**production** — `ws:` / `wss:` לפי הדף, עם `window.location.host` ונתיב `/ws`. אין משתנה `VITE_CHAT_WS_URL`. ב־Vite מוגדר גם proxy ל־`/ws` → 8081 (שימושי אם קוד אחר פונה לנתיב יחסי).
- **WebSocket נסיעות / התראות (Backend)** – `getWsBaseUrl()` ב־**DEV**: `ws://localhost:8000/api/v1`; בפרודקשן: אותו host + `/api/v1`.
- **Presence HTTP** – `GET /presence/...` דרך `chatWsApi`: ב־dev ה־Vite מפרוקסי `/presence` ל־`localhost:8081` (ראו `vite.config.ts`), בפרודקשן — דרך Nginx לאותו origin.
- `VITE_API_TIMEOUT_MS` – timeout לבקשות HTTP במילישניות (ברירת מחדל: `30000`).
- `VITE_GOOGLE_MAPS_API_KEY` – מפתח Google Maps להצגת מפה ונתיב נסיעה (אופציונלי; חלק מהמסכים עובדים גם בלעדיו).
- `VITE_GOOGLE_CLIENT_ID` – Client ID של Google OAuth (חובה לכניסה עם Google, בשימוש ב-`GoogleSignIn`).

הקובץ `src/config/env.ts` מרכז את הקריאה למשתנים האלה ומספק fallback הגיוני לסביבת פיתוח.

---

## סקריפטים שימושיים

- `npm run dev` – הרצה חיה עם HMR ב-`http://localhost:5173`.
- `npm run build` – בניית production ל-`dist/`.
- `npm run preview` – הרצת build מקומי לבדיקה.
- `npm run lint` – הרצת ESLint על TypeScript/React.

---

## נקודות מפתח בפרונטנד

- **RTL, עברית ואנגלית** – **i18next** + קבצים ב־`src/i18n/locales/{he,en}/`; **`LangContext`** מגדיר `dir` ו־`--font-primary` על `<html>`. פורמט תאריכים/שעות: **`src/utils/date.ts`** + **`getLocale()`**. Fallback לטקסטי שגיאת API ב־hooks: **`apiErr`** ב־`src/utils/i18nError.ts` (מפתחות `common:err_*`). **CSS Modules:** `font-family: var(--font-primary)` (חריג: `LangToggle`). ADR: **`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`** §10–12.
- **אימות** – קומפוננטות התחברות/הרשמה עובדות מול backend OAuth/JWT; תמיכה ב-Google Sign-In באמצעות `GoogleSignIn.tsx` ו-`VITE_GOOGLE_CLIENT_ID`. בצד השרת יש **rate limiting** על רישום והתחברות (Redis) — בבדיקות עומס או ניסיונות חוזרים מהירים אפשר לקבל 429; ראו `docs/architecture/API.md` ו-`backend/README.md`.
- **מיילים ארכיטקטורית** – רינדור תבניות מייל עבר ל-service ייעודי `email-renderer` (Node.js/Express + React Email) בצד הבקאנד/worker; לפרונט אין תלות ישירה, אבל תכני מייל/טמפלטים מנוהלים כעת ב-`email-renderer/src/emails/templates/`.
- **AI עוזר טקסט ליצירת נסיעה (CreateRide)** – הנהג מתאר נסיעה חופשית; הפרונט קורא ל-`POST /api/v1/passenger/passengers/ai-parse-search` וממלא שדות (מוצא/יעד/זמן/מקומות), עם follow-up מקומי לזמן חסר/לא תקף ובלי auto-submit.
- **ניהול קבוצות** – במסכי `GroupManage` אפשר ליצור קבוצה, לשתף קישור הזמנה, להעתיק URL בלחיצה עם פידבק חזותי (העתקה מוצלחת/שגיאה) ולסגור קבוצה.
- **צ'אט** – בפיתוח: WS ל־`chat-ws` ב־**8081** (`getChatWebSocketUrl`); בפרודקשן: `/ws` מאותו host (Nginx). **Presence:** טעינה חד־פעמית של `GET /presence/{partner}` דרך `chatWsApi` (proxy ל־8081 ב־dev); עדכון **מיידי** ב-WS: `user_online` / `user_offline`. אירועי `typing_start` / `typing_stop` מהשרת כוללים **`conversation_id`** ו־**`recipient_id`** (בנוסף ל־`user_id` ו־`type`; אופציונלי `full_name` ב־start) — כמו ב־`chat-ws` (`TypingPayload`); מסוננים בצד הלקוח מול echo של המשתמש הנוכחי. עיבוד הודעות ב־[`src/pages/MessageThread/processChatWebSocketMessage.ts`](src/pages/MessageThread/processChatWebSocketMessage.ts); בדיקות יחידה ב־[`processChatWebSocketMessage.test.ts`](src/pages/MessageThread/processChatWebSocketMessage.test.ts) משקפות את אותו חוזה. פירוט ערוצים ו-GPS: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **הזמנות שלי (My Bookings)** – טעינת נתונים ב־**קריאה מאוגדת לכל טאב**: [`fetchDriverSummary`](../src/api/bookings.ts) → `GET /bookings/driver-summary`, [`fetchPassengerSummary`](../src/api/bookings.ts) → `GET /bookings/passenger-summary` (במקום N+1 של מניפסטים / נסיעה+נהג). הוקים: [`useMyBookingsDriver.ts`](../src/pages/MyBookings/useMyBookingsDriver.ts), [`useMyBookingsPassenger.ts`](../src/pages/MyBookings/useMyBookingsPassenger.ts); [`useMyBookings.ts`](../src/pages/MyBookings/useMyBookings.ts) מחזיר מבנה מקונן (`passenger`, `driver`, `chat`) ו־**`MyBookingsViewModel`**. מיפוי DTO ל-UI מרוכז ב־[`myBookings.mappers.ts`](../src/pages/MyBookings/myBookings.mappers.ts). כרטיס נוסע בודד: [`PassengerBookingCard.tsx`](../src/pages/MyBookings/PassengerBookingCard.tsx).
- **מפה חיה / GPS (My Bookings)** – שידור מיקום נהג/נוסע דרך `useLocationBroadcast` / `usePassengerLocationBroadcast` + `useLocationWatcher` (throttle ~1.5s, `maximumAge: 0` לשידור); קבלת עדכונים ב־`useDriverLocation` / `usePassengerLocations` (WebSocket ל־backend, reconnect). מודלים `LiveMapModal` / `LiveRideMapModal`: `watchPosition` נפרד לתצוגת “אני” עם `maximumAge: 1000`; סמנים דרך `useMapMarker` (יצירה חד־פעמית, עדכון `setPosition` בלבד). פירוט: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **Zod + WebSocket** – סכימות ב־[`src/types/wsEvents.ts`](src/types/wsEvents.ts): אירועי נסיעה (`RideEventSchema`), מיקום נהג/נוסעים, צ’אט (`ChatPresenceEventSchema`), **הודעה נכנסת** (`ChatMessageSchema` → מיפוי מפורש ל־`MessageResponse` ב־`processChatWebSocketMessage`). `safeParse` גם ב־`useRideWebSocket`, `useDriverLocation`, `usePassengerLocations`, `MyRides`, `useUserEventStream`. סיכום: [`docs/ENGINEERING_HIGHLIGHTS.md`](../docs/ENGINEERING_HIGHLIGHTS.md).
- **פיד התראות in-app (מסך / באדג’ צ’אט)** – חיבור ל־**`/api/v1/notifications/ws`** דרך [`useChatNotificationsWebSocket.ts`](src/context/useChatNotificationsWebSocket.ts) + [`useReconnectingWebSocket.ts`](src/hooks/useReconnectingWebSocket.ts); ב־**`onOpen`** (גם אחרי reconnect) — רענון פיד, unread ואירוע `linkup-notifications-refresh`. גיבוי: [`useChatNotificationsFeed.ts`](src/context/useChatNotificationsFeed.ts) — polling REST כל **~5 דקות**. **FCM (דחיפה):** [`services/fcm.ts`](src/services/fcm.ts) — לוגי דיבאג עיקריים ב־**`devLog`** רק ב־`import.meta.env.DEV`; פירוט: [`docs/FCM_SYSTEM_SUMMARY.md`](../docs/FCM_SYSTEM_SUMMARY.md).

למידע רחב יותר על הארכיטקטורה וההרצה הכוללת (Docker, Kubernetes, chat-ws, mobile) ראו את ה-`README` בשורש הפרויקט.
