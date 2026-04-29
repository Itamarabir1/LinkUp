# LinkUp Frontend (React + Vite)

אפליקציית ווב ב-React + TypeScript (Vite) ל-LinkUp: ניהול נסיעות, קבוצות, צ'אט בזמן אמת, התחברות עם Google ואימייל/סיסמה, תמונות פרופיל (S3), **תמיכה ב-RTL ובאנגלית (i18next)** עם מעבר שפה, ופורמט תאריכים לפי לוקאל.

> **הערה:** ריצת Frontend CI ב-GitHub מופעלת כשקומיט משנה `frontend/**`, `nginx/**`, או את `.github/workflows/frontend-ci.yml`.

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
- `npm run size` – בדיקת תקציבי bundle עם `size-limit`.
- `npm run analyze` – build שמייצר דוח ויזואלי `dist/stats.html`.
- `npm run gen:api` – יצירת Orval client/types מ-`openapi-snapshot.json` לתיקיית `src/api/generated`.

---

## Bundle Budget B (Visualizer + manualChunks + size-limit)

- **Artifacts** – כל `npm run build` מייצר `dist/stats.html` בעזרת `rollup-plugin-visualizer` (gzip + brotli).
- **Manual chunk policy** – ספקים כבדים מפוצלים ל-chunks ייעודיים: `react-vendor`, `query`, `firebase`, `sentry`, `i18n`, `forms`, `charts`.
- **Admin charts isolation** – `recharts` מופרד ב-`charts-*` כדי למנוע זליגה ל-main chunk.
- **Devtools guardrail** – `@tanstack/react-query-devtools` לא מוכנס ידנית ל-prod vendor chunks; הוא נשאר מבוסס lazy/DEV gating ברמת האפליקציה.
- **Budget enforcement** – `npm run size` מאמת גבולות גודל לכל chunk קריטי דרך סעיף `size-limit` ב-`package.json`.
- **Triage when budget fails** – פותחים `dist/stats.html`, מזהים מי נכנס ל-chunk החורג, ומשנים budget רק אם יש גידול מכוון ומוצדק (לא מעלים limits אוטומטית).

---

## OpenAPI / Orval CI Gate

- **Source of truth** – קבצי `src/api/generated/*` מחויבים ל-git כחלק מחוזה API reviewable.
- **CI enforcement** – ב-`frontend-ci` יש job ייעודי `contract-codegen` שמריץ:
  - `npm run gen:api`
  - `git update-index -q --refresh`
  - `git diff --exit-code -- src/api/generated/`
- **Failure action** – אם CI נכשל על drift, מריצים מקומית `npm run gen:api`, מקמיטים את השינויים ב-`src/api/generated`, ודוחפים מחדש.

---

## Web Vitals D — Sentry RUM

- **Production-only instrumentation** – `Sentry.init` רץ רק תחת `import.meta.env.PROD && APP_CONFIG.sentry.dsn`.
- **RUM stack** – `BrowserTracing` + `Replay` עם הגדרות פרטיות (`maskAllText`, `blockAllMedia`).
- **Quota-safe sampling** – `replaysSessionSampleRate: 0.05`, `replaysOnErrorSampleRate: 1.0`.
- **Web Vitals metrics** – `CLS`, `LCP`, `INP` נשלחים ל-Sentry metrics דרך dynamic import של `web-vitals` (מונע כניסה ל-main bundle).
- **Auth identity alignment** – `AuthContext` מעדכן `Sentry.setUser` ב-bootstrap/login/google-login ומאפס ב-logout לקבלת traces/replays מיוחסים למשתמש.
- **Guardrail** – אין הפעלת Sentry/RUM במצב dev.

## Sentry Sourcemaps Upload

- **Plugin** – הפרויקט משתמש ב-`@sentry/vite-plugin` ב-`vite.config.ts`.
- **Activation policy** – ה-plugin מופעל רק ב-`mode=production` ורק כשקיימים `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`.
- **CI path** – ב-`frontend-ci` הסודות מוזרקים רק ב-job של `publish-image` (main push), ולא ב-PR quality build.
- **Artifact hygiene** – `filesToDeleteAfterUpload: ['dist/**/*.map']` מוחק sourcemaps אחרי upload כדי שלא ייכנסו ל-image של nginx.

---

## נקודות מפתח בפרונטנד

- **RTL, עברית ואנגלית** – **i18next** + קבצים ב־`src/i18n/locales/{he,en}/`; **`LangContext`** מגדיר `dir` ו־`--font-primary` על `<html>`. פורמט תאריכים/שעות: **`src/utils/date.ts`** + **`getLocale()`**. Fallback לטקסטי שגיאת API ב־hooks: **`apiErr`** ב־`src/utils/i18nError.ts` (מפתחות `common:err_*`). **CSS Modules:** `font-family: var(--font-primary)` (חריג: `LangToggle`). ADR: **`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`** §10–12.
- **אימות** – קומפוננטות Login/Register/VerifyEmail מבוססות `react-hook-form + zod` עם שמירת behavior parity מול הזרימה הקיימת (אותם API calls, אותם נתיבי navigation ואותן הודעות שגיאה כלליות). ב-`Register` שדה `PhoneInput` מחובר דרך `Controller`. תמיכה ב-Google Sign-In באמצעות `GoogleSignIn.tsx` ו-`VITE_GOOGLE_CLIENT_ID`. בצד השרת יש **rate limiting** על רישום והתחברות (Redis) — בבדיקות עומס או ניסיונות חוזרים מהירים אפשר לקבל 429; ראו `docs/architecture/API.md` ו-`backend/README.md`.
- **מיילים ארכיטקטורית** – רינדור תבניות מייל עבר ל-service ייעודי `email-renderer` (Node.js/Express + React Email) בצד הבקאנד/worker; לפרונט אין תלות ישירה, אבל תכני מייל/טמפלטים מנוהלים כעת ב-`email-renderer/src/emails/templates/`.
- **Premium / Billing UX** – הפרונט כולל אינטגרציה מלאה ל-`/api/v1/billing`: `PremiumBanner` במסך הפרופיל (badge למנוי פעיל או upgrade CTA), mutation ל-Stripe checkout, ועמודי תוצאה מוגנים `payment/success` + `payment/cancel`. מסך success מבצע polling ל-`/billing/status` כל 2 שניות עד אישור `is_premium` או timeout של 30 שניות.
- **Stage 3a — React Query (Geo + Notifications + Auth-shadow)** – `useGoogleMapsKey` עובד דרך `useQuery` עם `qk.geo.mapsKey` ו-cache ארוך טווח; `Notifications` עבר מ-fetch ידני ל-`qk.notifications.all` עם invalidate מאירוע `linkup-notifications-refresh`; `AuthContext` מסנכרן cache של `qk.auth.me()` אחרי login/sign-in, מנקה cache ב-logout (`queryClient.clear()`), ונוסף `useCurrentUser()` query hook לצרכנים מבוססי RQ.
- **Stage 3b Part 2 — React Query (MyBookings Driver + Passenger)** – הוקי `useMyBookingsPassenger`/`useMyBookingsDriver` עובדים דרך `useQuery` עם keys scoped לפי משתמש (`qk.bookings.passenger(userId)`, `qk.bookings.driver(userId)`), פעולות approve/reject/cancel עברו ל-`useMutation`, ואירועי WS מבצעים invalidate/query updates במקום fetch ידני; נשמרו `driverStatus` machine, local UI state וחוזה ההחזרה ל-`useMyBookings`.
- **Stage 3b Part 6 — React Query (SearchRides network edges)** – [`useSearchRides.ts`](src/pages/SearchRides/useSearchRides.ts) עבר ממימוש ידני ל-mutations עבור `search`, `load more`, ו-`save alert`; נשמרו `useOperationToken`, AI parse flow, geolocation flow, וחוזה ההחזרה ל-UI. [`useJoinRide.ts`](src/pages/SearchRides/useJoinRide.ts) נשאר ללא שינוי כדי לשמר `idempotencyKeyRef` request-scoped.
- **Stage 3c — Admin RQ completion** – מסכי admin עובדים בתבנית RQ, כולל `AdminLookup` שעבר מ-manual async/result state ל-`useMutation` עבור lookup יזום משתמש (ride/booking) תוך שמירת UI parity.
- **Stage 5 cleanup — React Query + auth boot safety** – [`useMyRequests.ts`](src/pages/useMyRequests.ts) הומר ל-`useQuery`/`useMutation` עם cache patching ל-cancel/expire, ובמקביל תוקן initial-load effect ב-[`AuthContext.tsx`](src/context/AuthContext.tsx) ל-cancellable async pattern במקום `mounted` dead-check.
- **Web Vitals D — Sentry RUM + vitals metrics** – [`main.tsx`](src/main.tsx) מרחיב Sentry ב-PROD עם BrowserTracing/Replay sampling ודיווח `CLS/LCP/INP` מ-`web-vitals` ב-dynamic import; [`AuthContext.tsx`](src/context/AuthContext.tsx) מסנכרן `Sentry.setUser` ב-bootstrap/login/google-login ומנקה ב-logout.
- **Stage 3d — Chat RQ (safe subset)** – שכבות polling/fetch בצ׳אט הועברו ל-React Query בלי לשנות שכבות WS הקריטיות: [`useChatUnreadMessages.ts`](src/context/useChatUnreadMessages.ts) משתמש ב-`qk.chat.unread()` + `refetchInterval` במקום `setInterval`, [`useChatNotificationsFeed.ts`](src/context/useChatNotificationsFeed.ts) משתמש ב-`qk.notifications.all()` + invalidate refresh API במקום polling ידני, ו-[`Messages.tsx`](src/pages/Messages.tsx) משתמש ב-`qk.chat.conversations()` במקום fetch ידני; נשמרו semantics של מיון/טעינה/שגיאה ותאימות ל-`ChatContext`.
- **AI עוזר טקסט ליצירת נסיעה (CreateRide)** – הנהג מתאר נסיעה חופשית; הפרונט קורא ל-`POST /api/v1/passenger/passengers/ai-parse-search` וממלא שדות (מוצא/יעד/זמן/מקומות), עם follow-up מקומי לזמן חסר/לא תקף ובלי auto-submit.
- **ניהול קבוצות** – במסכי `GroupManage` אפשר ליצור קבוצה, לשתף קישור הזמנה, להעתיק URL בלחיצה עם פידבק חזותי (העתקה מוצלחת/שגיאה) ולסגור קבוצה.
- **צ'אט** – בפיתוח: WS ל־`chat-ws` ב־**8081** (`getChatWebSocketUrl`); בפרודקשן: `/ws` מאותו host (Nginx). **Presence:** טעינה חד־פעמית של `GET /presence/{partner}` דרך `chatWsApi` (proxy ל־8081 ב־dev); עדכון **מיידי** ב-WS: `user_online` / `user_offline`. אירועי `typing_start` / `typing_stop` מהשרת כוללים **`conversation_id`** ו־**`recipient_id`** (בנוסף ל־`user_id` ו־`type`; אופציונלי `full_name` ב־start) — כמו ב־`chat-ws` (`TypingPayload`); מסוננים בצד הלקוח מול echo של המשתמש הנוכחי. עיבוד הודעות ב־[`src/pages/MessageThread/processChatWebSocketMessage.ts`](src/pages/MessageThread/processChatWebSocketMessage.ts); בדיקות יחידה ב־[`processChatWebSocketMessage.test.ts`](src/pages/MessageThread/processChatWebSocketMessage.test.ts) משקפות את אותו חוזה. פירוט ערוצים ו-GPS: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **הזמנות שלי (My Bookings)** – טעינת נתונים ב־**קריאה מאוגדת לכל טאב**: [`fetchDriverSummary`](../src/api/bookings.ts) → `GET /bookings/driver-summary`, [`fetchPassengerSummary`](../src/api/bookings.ts) → `GET /bookings/passenger-summary` (במקום N+1 של מניפסטים / נסיעה+נהג). ב־Stage 3b Part 2 ה-hooks [`useMyBookingsDriver.ts`](../src/pages/MyBookings/useMyBookingsDriver.ts), [`useMyBookingsPassenger.ts`](../src/pages/MyBookings/useMyBookingsPassenger.ts) הומרו ל-React Query (keys scoped לפי user + mutations + WS invalidate), תוך שמירה על חוזה החזרה זהה ל-[`useMyBookings.ts`](../src/pages/MyBookings/useMyBookings.ts) ול־**`MyBookingsViewModel`**. מיפוי DTO ל-UI נשאר מרוכז ב־[`myBookings.mappers.ts`](../src/pages/MyBookings/myBookings.mappers.ts). כרטיס נוסע בודד: [`PassengerBookingCard.tsx`](../src/pages/MyBookings/PassengerBookingCard.tsx).
- **מפה חיה / GPS (My Bookings)** – שידור מיקום נהג/נוסע דרך `useLocationBroadcast` / `usePassengerLocationBroadcast` + `useLocationWatcher` (throttle ~1.5s, `maximumAge: 0` לשידור); קבלת עדכונים ב־`useDriverLocation` / `usePassengerLocations` (WebSocket ל־backend, reconnect). מודלים `LiveMapModal` / `LiveRideMapModal`: `watchPosition` נפרד לתצוגת “אני” עם `maximumAge: 1000`; סמנים דרך `useMapMarker` (יצירה חד־פעמית, עדכון `setPosition` בלבד). פירוט: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **Zod + WebSocket** – סכימות ב־[`src/types/wsEvents.ts`](src/types/wsEvents.ts): אירועי נסיעה (`RideEventSchema`), מיקום נהג/נוסעים, צ’אט (`ChatPresenceEventSchema`), **הודעה נכנסת** (`ChatMessageSchema` → מיפוי מפורש ל־`MessageResponse` ב־`processChatWebSocketMessage`). `safeParse` גם ב־`useRideWebSocket`, `useDriverLocation`, `usePassengerLocations`, `MyRides`, `useUserEventStream`. סיכום: [`docs/ENGINEERING_HIGHLIGHTS.md`](../docs/ENGINEERING_HIGHLIGHTS.md).
- **פיד התראות in-app (מסך / באדג’ צ’אט)** – חיבור ל־**`/api/v1/notifications/ws`** דרך [`useChatNotificationsWebSocket.ts`](src/context/useChatNotificationsWebSocket.ts) + [`useReconnectingWebSocket.ts`](src/hooks/useReconnectingWebSocket.ts); ב־**`onOpen`** (גם אחרי reconnect) — רענון פיד, unread ואירוע `linkup-notifications-refresh`. גיבוי: [`useChatNotificationsFeed.ts`](src/context/useChatNotificationsFeed.ts) — polling REST כל **~5 דקות**. **FCM (דחיפה):** [`services/fcm.ts`](src/services/fcm.ts) — לוגי דיבאג עיקריים ב־**`devLog`** רק ב־`import.meta.env.DEV`; פירוט: [`docs/FCM_SYSTEM_SUMMARY.md`](../docs/FCM_SYSTEM_SUMMARY.md).
- **שכבות WS שלא שונו במכוון במיגרציית Stage 3d** – [`useConversationMessages`](src/pages/MessageThread/useConversationMessages.ts), [`useChatPopup`](src/context/useChatPopup.ts), [`useChatWebSocket`](src/context/useChatWebSocket.ts), ו-[`processChatWebSocketMessage`](src/pages/MessageThread/processChatWebSocketMessage.ts) נשארו transport/message-stream raw כדי לשמור יציבות בזמן מיגרציה מדורגת.

למידע רחב יותר על הארכיטקטורה וההרצה הכוללת (Docker, Kubernetes, chat-ws, mobile) ראו את ה-`README` בשורש הפרויקט.

