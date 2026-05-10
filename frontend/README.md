# LinkUp Frontend (React + Vite)

אפליקציית ווב ב-React + TypeScript (Vite) ל-LinkUp: ניהול נסיעות, קבוצות, צ'אט בזמן אמת, התחברות עם Google ואימייל/סיסמה, תמונות פרופיל (S3), **תמיכה ב-RTL ובאנגלית (i18next)** עם מעבר שפה, ופורמט תאריכים לפי לוקאל.

> **הערה:** ריצת Frontend CI ב-GitHub מופעלת כשקומיט משנה `frontend/**`, `nginx/**`, או את `.github/workflows/frontend-ci.yml`. בפרודקשן (EC2), אחרי ש־**Frontend CI** (או CI אחר של שירות על **`main`**) מסתיים בהצלחה, **[`deploy-ec2.yml`](../.github/workflows/deploy-ec2.yml)** מריץ פריסת Compose מלאה כולל **`frontend`** + **`nginx`** (פרטים: **[`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)**).

### אבטחה (XSS + CSP)

- **באפליקציה:** ESLint **`react/no-danger`** (חוסם) ו־**`sanitizeHtml()`** (`src/utils/sanitize.ts`, DOMPurify).
- **מעטפת HTML:** קובץ סטטי **`public/bootstrap.js`** (מוגש כ־**`/bootstrap.js`**) — שפה (`linkup-lang`) וערכת נושא (`linkup-theme`) לפני הידרציה; נטען ב־**`index.html` לפני `config.js`** כדי לאפשר **`script-src`** ב-CSP **בלי** **`'unsafe-inline'`** ב־nginx.
- **בפרודקשן מאחורי Compose nginx:** כותרת **`Content-Security-Policy`** ב־**`nginx/nginx.conf.template`** (רינדור ל־`nginx/nginx.conf` עם **`scripts/ops/render-nginx-conf.sh`** / CI, ו־**`SENTRY_REPORT_URI`** ב־`backend/.env`). מדריך: **[`docs/SECURITY_HEADERS.md`](../docs/SECURITY_HEADERS.md)**.

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
- **REST צ’אט — Idempotency-Key + UI אופטימי:** [`src/api/chat.ts`](src/api/chat.ts) **`sendMessage`** שולח **`Idempotency-Key`** (אופציונלי מבחוץ; אחרת UUID). **`useMessageThread`** / **`useChatPopup`** מעבירים מפתח יציב לניסיון שליחה (**`utils/outboundIdempotencyKey.ts`**), מחזיקים רשימה כ־**`ChatListRow`** (**`types/chatList.ts`**) עם בועת **pending**, ומאחדים תשובות שרת/WS עם **`applyInboundRealMessage`** + **`appendMessageDedupById`** (**`utils/chatMessagesMerge.ts`**); כשל שליחה — **`removePendingByClientId`**. תואם ל־Stripe-style בבקאנד (**ADR §25**; פרונט **`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md` §2**; היילייטס **`docs/ENGINEERING_HIGHLIGHTS.md`**).
- `VITE_API_TIMEOUT_MS` – timeout לבקשות HTTP במילישניות (ברירת מחדל: `30000`).
- `VITE_GOOGLE_MAPS_API_KEY` – מפתח Google Maps להצגת מפה ונתיב נסיעה (אופציונלי; חלק מהמסכים עובדים גם בלעדיו).
- `VITE_GOOGLE_CLIENT_ID` – Client ID של Google OAuth (חובה לכניסה עם Google, בשימוש ב-`GoogleSignIn`).

הקובץ `src/config/env.ts` מרכז את הקריאה למשתנים האלה ומספק fallback הגיוני לסביבת פיתוח.

### צ’אט — השלמת הודעות אחרי ניתוק (REST)

כל **`onOpen`** של צ’אט WS מפעיל **`fetchMissedMessages`** → **`fetchMissedGap`** ([`src/pages/MessageThread/fetchMissedGap.ts`](src/pages/MessageThread/fetchMissedGap.ts)): עמוד ראשון עם **`after=`**, המשך עם **`before=next_cursor`** עד **`has_more`** או תקרת לקוח. פירוט: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).

### WebSocket — ניתוק transport וניסיון חיבור מחדש

עיכוב בין ניסיונות reconnect אחרי **`onclose`** / שגיאת ctor: **`computeReconnectDelayMs`** ב־[`src/utils/reconnectBackoff.ts`](src/utils/reconnectBackoff.ts) (מעריכה, תקרת 30s, ±20% jitter) — **`useChatWebSocket`**, **`useReconnectingWebSocket`**, **`useReconnectingWebSocketState`**. ראו [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md) ו־[`docs/FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff`](../docs/FEATURE_DECISIONS.md#frontend-ws-reconnect-backoff).

---

## סקריפטים שימושיים

- `npm run dev` – הרצה חיה עם HMR ב-`http://localhost:5173`.
- `npm run build` – בניית production ל-`dist/`.
- `npm run preview` – הרצת build מקומי לבדיקה.
- `npm run lint` – הרצת ESLint על TypeScript/React.
- `npm run size` – בדיקת תקציבי bundle עם `size-limit`.
- `npm run analyze` – build שמייצר דוח ויזואלי `dist/stats.html`.
- `npm run gen:api` – יצירת Orval client/types מ-`openapi-snapshot.json` לתיקיית `src/api/generated`. (ה-snapshot עצמו הוא תוצר build, gitignored — מיוצא אוטומטית מ-FastAPI דרך `npm run openapi:sync` או `make openapi`.)
- `npm run openapi:sync` – סנכרון מלא: מייצא OpenAPI מ-`app.openapi()`, רץ Orval, ומציג את ה-diff. רץ `make openapi` בשורש.

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

- **Source of truth** – `app.openapi()` ב-FastAPI ([`backend/app/main.py`](../backend/app/main.py)). הצרכן בפרונט הוא `src/api/generated/*` שנכנס ל-git כחוזה reviewable.
- **Build artifact (gitignored)** – `frontend/openapi-snapshot.json` הוא תוצר ביניים שמיוצא דרך [`backend/scripts/export_openapi.py`](../backend/scripts/export_openapi.py) (פלט דטרמיניסטי: `indent=2, sort_keys=True, ensure_ascii=False`); לא מקמיט.
- **CI enforcement** – workflow ייעודי [`.github/workflows/openapi-contract.yml`](../.github/workflows/openapi-contract.yml) (לא חלק מ-`frontend-ci`) מבצע: `uv sync` → `python backend/scripts/export_openapi.py` → `npm run gen:api` → `git diff --exit-code -- frontend/src/api/generated/`. שינוי schema בלי regeneration — מפיל את ה-PR.
- **Failure action** – מריצים מקומית `npm run openapi:sync` (או `make openapi` בשורש), מקמיטים שינויים ב-`src/api/generated`, ודוחפים מחדש.

---

## Web Vitals D — Sentry RUM

- **Production-only instrumentation** – `Sentry.init` רץ רק תחת `import.meta.env.PROD && APP_CONFIG.sentry.dsn`.
- **RUM stack** – `BrowserTracing` + `Replay` עם הגדרות פרטיות (`maskAllText`, `blockAllMedia`).
- **Quota-safe sampling** – `replaysSessionSampleRate: 0.05`, `replaysOnErrorSampleRate: 1.0`.
- **Web Vitals metrics** – `CLS`, `LCP`, `INP` נשלחים ל-Sentry metrics דרך dynamic import של `web-vitals` (מונע כניסה ל-main bundle).
- **Auth identity alignment** – `AuthContext` מעדכן `Sentry.setUser` ב-bootstrap/login/google-login ומאפס בכל ניתוח סשן מוסכם דרך **`tearDownSession`** (כולל **`session-expired`** / **`bootstrap-failed`**) — ראו למטה בסעיף **Auth session teardown**.
- **Guardrail** – אין הפעלת Sentry/RUM במצב dev.

## Sentry Sourcemaps Upload

- **Plugin** – הפרויקט משתמש ב-`@sentry/vite-plugin` ב-`vite.config.ts`.
- **Activation policy** – ה-plugin מופעל רק ב-`mode=production` ורק כשקיימים `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`.
- **CI path** – ב-`frontend-ci` הסודות מוזרקים רק ב-job של `publish-image` (main push), ולא ב-PR quality build.
- **Artifact hygiene** – `filesToDeleteAfterUpload: ['dist/**/*.map']` מוחק sourcemaps אחרי upload כדי שלא ייכנסו ל-image של nginx.

---

## Auth session teardown

- **`AuthContext.tsx`:** **`tearDownSession({ reason: 'user-action' | 'session-expired' | 'bootstrap-failed' })`** — **`user-action`:** `PATCH` FCM null + **`POST /auth/logout`** (when access still valid), then **`cleanupFCM`**, **`queryClient.clear()`**, **`Sentry.setUser(null)`** (PROD), **`clearTokens`**, unauthenticated state. **`session-expired` / `bootstrap-failed`:** local cleanup only (no server PATCH/logout with dead JWT).
- **`client.ts`:** failed or missing **`refreshAccessToken`** → **`clearTokens()`** + **`window.dispatchEvent('auth:session-expired')`** via **`emitSessionExpired`** (single-flight guard); refresh interceptor sets **`__sentryCaptured`** on final **401** before reject.
- **`queryClient.ts`:** **`shouldSkipSentryForApiError`** — **401** only (403/5xx flow to **`captureExceptionOnce`** subject to interceptor marking).
- **Docs:** **[`docs/FEATURE_DECISIONS.md`](../docs/FEATURE_DECISIONS.md#auth-session-teardown)** · **ADR Frontend §21**.

---

## נקודות מפתח בפרונטנד

- **RTL, עברית ואנגלית** – **i18next** + קבצים ב־`src/i18n/locales/{he,en}/`; **`LangContext`** מגדיר `dir` ו־`--font-primary` על `<html>`. פורמט תאריכים/שעות: **`src/utils/date.ts`** + **`getLocale()`**. Fallback לטקסטי שגיאת API ב־hooks: **`apiErr`** ב־`src/utils/i18nError.ts` (מפתחות `common:err_*`). **CSS Modules:** `font-family: var(--font-primary)` (חריג: `LangToggle`). ADR: **`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`** §10–12.
- **אימות** – קומפוננטות Login/Register/VerifyEmail מבוססות `react-hook-form + zod` עם שמירת behavior parity מול הזרימה הקיימת (אותם API calls, אותם נתיבי navigation ואותן הודעות שגיאה כלליות). ב-`Register` שדה `PhoneInput` מחובר דרך `Controller`. תמיכה ב-Google Sign-In באמצעות `GoogleSignIn.tsx` ו-`VITE_GOOGLE_CLIENT_ID`. בצד השרת יש **rate limiting** על רישום והתחברות (Redis) — בבדיקות עומס או ניסיונות חוזרים מהירים אפשר לקבל 429; ראו `docs/architecture/API.md` ו-`backend/README.md`.
- **מיילים ארכיטקטורית** – רינדור תבניות מייל עבר ל-service ייעודי `email-renderer` (Node.js/Express + React Email) בצד הבקאנד/worker; לפרונט אין תלות ישירה, אבל תכני מייל/טמפלטים מנוהלים כעת ב-`email-renderer/src/emails/templates/`.
- **Premium / Billing UX** – הפרונט כולל אינטגרציה ל-`/api/v1/billing`: `PremiumBanner`, mutation ל-Stripe checkout, ועמודי `payment/success` + `payment/cancel` עם polling ל-`/billing/status`. בבקאנד: **`docs/BILLING_REFACTOR_SUMMARY.md`** (סיכום מלא); גם **`docs/FEATURE_DECISIONS.md`** (סעיף billing-checkout-db-idempotency-reconciler).
- **Stage 3a — React Query (Geo + Notifications + Auth-shadow)** – `useGoogleMapsKey` עובד דרך `useQuery` עם `qk.geo.mapsKey` ו-cache ארוך טווח; `Notifications` עבר מ-fetch ידני ל-query keys ייעודיים (`qk.notifications.page(limit)` למסך עם `useInfiniteQuery`, `qk.notifications.all()` לבאדג'ים) עם invalidate מאירוע `linkup-notifications-refresh`; `AuthContext` מסנכרן cache של `qk.auth.me()` אחרי login/sign-in, מנקה cache ב-logout (`queryClient.clear()`), ונוסף `useCurrentUser()` query hook לצרכנים מבוססי RQ.
- **Stage 3b Part 2 — React Query (MyBookings Driver + Passenger)** – `useQuery` ל**פעיל** (`qk.bookings.driverActive` / `passengerActive`) ו-`useInfiniteQuery` ל**היסטוריה** (`driverHistory` / `passengerHistory`) מול `/bookings/*-summary/active` + `/history`; invalidate כפול אחרי mutations/WS; נשמרו `driverStatus`, `useLocationBroadcast`, ו-`useMyBookings` / **`MyBookingsViewModel`** (`activeItems`, `historyItems`, «טען עוד»).
- **Stage 3b Part 6 — React Query (SearchRides network edges)** – [`useSearchRides.ts`](src/pages/SearchRides/useSearchRides.ts) עבר ממימוש ידני ל-mutations עבור `search`, `load more`, ו-`save alert`; נשמרו `useOperationToken`, AI parse flow, geolocation flow, וחוזה ההחזרה ל-UI. **סינון זמן ב־API:** [`buildManualRideSearchParams`](src/pages/SearchRides/useSearchRides.ts) לפי **`searchMode`** (`date_only` → `departure_date`; `time_range` → `departure_time`+`departure_time_to`; אחרת נקודת זמן) + [`buildParamsFromAiResult`](src/pages/SearchRides/useSearchRides.ts) לחיפוש אוטומטי אחרי AI. [`useJoinRide.ts`](src/pages/SearchRides/useJoinRide.ts) נשאר ללא שינוי כדי לשמר `idempotencyKeyRef` request-scoped.
- **Stage 3c — Admin RQ completion** – מסכי admin עובדים בתבנית RQ, כולל `AdminLookup` שעבר מ-manual async/result state ל-`useMutation` עבור lookup יזום משתמש (ride/booking) תוך שמירת UI parity.
- **Stage 5 cleanup — React Query + auth boot safety** – [`useMyRequests.ts`](src/pages/useMyRequests.ts) משתמש ב-`useInfiniteQuery`/`useMutation` מעל **`GET …/passenger/passengers/me`** בתגובה cursor pagination (**`PaginatedPassengerRequestsResponse`**: `items`, `next_cursor`, `has_more`; fetch עם `limit=100` ו-`cursor` לפי `getNextPageParam`), ו-cache patching ל־cancel/`REQUEST_EXPIRED` עובד על `InfiniteData.pages`. initial-load ב-[`AuthContext.tsx`](src/context/AuthContext.tsx) — cancellable async pattern במקום `mounted` dead-check.
- **Web Vitals D — Sentry RUM + vitals metrics** – [`main.tsx`](src/main.tsx) מרחיב Sentry ב-PROD עם BrowserTracing/Replay sampling ודיווח `CLS/LCP/INP` מ-`web-vitals` ב-dynamic import; [`AuthContext.tsx`](src/context/AuthContext.tsx) מסנכרן `Sentry.setUser` ב-bootstrap/login/google-login ומנקה ב-logout.
- **Stage 3d — Chat RQ (safe subset)** – שכבות polling/fetch בצ׳אט הועברו ל-React Query בלי לשנות שכבות WS הקריטיות: [`useChatUnreadMessages.ts`](src/context/useChatUnreadMessages.ts) משתמש ב-`qk.chat.unread()` + `refetchInterval` במקום `setInterval`, [`useChatNotificationsFeed.ts`](src/context/useChatNotificationsFeed.ts) משתמש ב-`qk.notifications.all()` + invalidate refresh API במקום polling ידני, ו-[`Messages.tsx`](src/pages/Messages.tsx) משתמש ב-`useInfiniteQuery` + `qk.chat.conversations(limit)` + `listConversations({ limit, after })` — cursor pagination מהשרת (בלי מיון ידני בצד לקוח); תאימות ל-`ChatContext`.
- **AI עוזר טקסט ליצירת נסיעה (CreateRide)** – הנהג מתאר נסיעה חופשית; הפרונט קורא ל-`POST /api/v1/passenger/passengers/ai-parse-search` וממלא שדות (מוצא/יעד/זמן/מקומות), עם follow-up מקומי לזמן חסר/לא תקף ובלי auto-submit.
- **ניהול קבוצות** – במסכי `GroupManage` אפשר ליצור קבוצה, לשתף קישור הזמנה, להעתיק URL בלחיצה עם פידבק חזותי (העתקה מוצלחת/שגיאה) ולסגור קבוצה.
- **צ'אט** – בפיתוח: WS ל־`chat-ws` ב־**8081** (`getChatWebSocketUrl`); בפרודקשן: `/ws` מאותו host (Nginx). **Presence:** טעינה חד־פעמית של `GET /presence/{partner}` דרך `chatWsApi` (proxy ל־8081 ב־dev); עדכון **מיידי** ב-WS: `user_online` / `user_offline`. אירועי `typing_start` / `typing_stop` מהשרת כוללים **`conversation_id`** ו־**`recipient_id`** (בנוסף ל־`user_id` ו־`type`; אופציונלי `full_name` ב־start) — כמו ב־`chat-ws` (`TypingPayload`); מסוננים בצד הלקוח מול echo של המשתמש הנוכחי. עיבוד הודעות ב־[`src/pages/MessageThread/processChatWebSocketMessage.ts`](src/pages/MessageThread/processChatWebSocketMessage.ts); בדיקות יחידה ב־[`processChatWebSocketMessage.test.ts`](src/pages/MessageThread/processChatWebSocketMessage.test.ts) משקפות את אותו חוזה. פירוט ערוצים ו-GPS: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **הזמנות שלי (My Bookings)** – **פעיל** + **היסטוריה עם cursor**: [`fetchDriverActive`](../src/api/bookings.ts) / [`fetchDriverHistory`](../src/api/bookings.ts), ומקבילות לנוסע — מול `GET /bookings/driver-summary/active|history` (ו-passenger). [`useMyBookingsDriver.ts`](../src/pages/MyBookings/useMyBookingsDriver.ts) / [`useMyBookingsPassenger.ts`](../src/pages/MyBookings/useMyBookingsPassenger.ts): `useQuery` + `useInfiniteQuery`, invalidate לשני סוגי המפתכים; [`useMyBookings.ts`](../src/pages/MyBookings/useMyBookings.ts) ו-**`MyBookingsViewModel`**. [`myBookings.mappers.ts`](../src/pages/MyBookings/myBookings.mappers.ts); [`PassengerBookingCard.tsx`](../src/pages/MyBookings/PassengerBookingCard.tsx).
- **מפה חיה / GPS (My Bookings)** – שידור מיקום נהג/נוסע דרך `useLocationBroadcast` / `usePassengerLocationBroadcast` + `useLocationWatcher` (throttle ~1.5s, `maximumAge: 0` לשידור); קבלת עדכונים ב־`useDriverLocation` / `usePassengerLocations` (WebSocket ל־backend עם reconnect — **exponential backoff + jitter** דרך [`reconnectBackoff.ts`](src/utils/reconnectBackoff.ts)). מודלים `LiveMapModal` / `LiveRideMapModal`: `watchPosition` נפרד לתצוגת “אני” עם `maximumAge: 1000`; סמנים דרך `useMapMarker` (יצירה חד־פעמית, עדכון `setPosition` בלבד). פירוט: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **Zod + WebSocket** – סכימות ב־[`src/types/wsEvents.ts`](src/types/wsEvents.ts): אירועי נסיעה (`RideEventSchema`), מיקום נהג/נוסעים, **`InvalidateEventSchema`**, צ’אט (`ChatPresenceEventSchema`; כולל `unread_count` לפריימים מערוץ השיחה), **הודעה נכנסת** (`ChatMessageSchema`). `safeParse` ב־`useRideWebSocket`, `useDriverLocation`, `usePassengerLocations`, `MyRides`, **`useUserEventStream`**, `processChatWebSocketMessage`. סיכום: [`docs/ENGINEERING_HIGHLIGHTS.md`](../docs/ENGINEERING_HIGHLIGHTS.md).
- **פיד התראות in-app (מסך / באדג’ צ’אט)** – `GET /api/v1/users/me/notifications` מחזיר `items`, `next_cursor`, `has_more`, `limit`. מסך Notifications משתמש ב-`useInfiniteQuery` + `qk.notifications.page(20)` (load more לפי `next_cursor`); `useChatNotificationsFeed.ts` לבאדג'ים משתמש בעמוד ראשון בלבד (`limit=20`) עם polling ~**5 דקות**. רענון חי: **`useUserEventStream`** ב־[`ChatContext.tsx`](src/context/ChatContext.tsx) — פריים **`invalidate`** / **`UserEvent`**; בענף **`notifications`** — גם **`NOTIFICATIONS_REFRESH_EVENT`** ו־**`linkup:user-event`**. באדג’ הודעות — **`setUnreadDirect`** / invalidate מ־**`unread_messages`**. פריימי **`unread_count`** בערוץ השיחה נשארים ב־[**`wsEvents.ts`**](src/types/wsEvents.ts) / **`processChatWebSocketMessage`**. **FCM:** [`services/fcm.ts`](src/services/fcm.ts) — **`devLog`** ב־DEV; פירוט: [`docs/FCM_SYSTEM_SUMMARY.md`](../docs/FCM_SYSTEM_SUMMARY.md).
- **שכבות WS שלא שונו במכוון במיגרציית Stage 3d** – [`useConversationMessages`](src/pages/MessageThread/useConversationMessages.ts), [`useChatPopup`](src/context/useChatPopup.ts), [`useChatWebSocket`](src/context/useChatWebSocket.ts), ו-[`processChatWebSocketMessage`](src/pages/MessageThread/processChatWebSocketMessage.ts) נשארו transport/message-stream raw כדי לשמור יציבות בזמן מיגרציה מדורגת.
- **MyRides ב־React Query** – [`MyRides.tsx`](src/pages/MyRides.tsx): `qk.rides.list()` + מוטציית ביטול + רענון מ־`useUserEvent` / `useRideWebSocket`.

**Backlog פרונט (checklist מעודכן):** [`docs/FRONTEND_UPGRADE_ROADMAP.md`](../docs/FRONTEND_UPGRADE_ROADMAP.md).

למידע רחב יותר על הארכיטקטורה וההרצה הכוללת (Docker Compose, chat-ws, mobile) ראו את ה-`README` בשורש הפרויקט.
