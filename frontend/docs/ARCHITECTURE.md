# Frontend architecture (LinkUp)

רשימת ריפקטור ואיכות מלאה (מקור אמת): [`FRONTEND_REFACTOR_AND_QUALITY.md`](./FRONTEND_REFACTOR_AND_QUALITY.md). **מה פתוח / checklist מעודכן:** [`../../docs/FRONTEND_UPGRADE_ROADMAP.md`](../../docs/FRONTEND_UPGRADE_ROADMAP.md). סיכום להצגה בפורטפוליו: [`../../docs/ENGINEERING_HIGHLIGHTS.md`](../../docs/ENGINEERING_HIGHLIGHTS.md) (סעיף 14).

הערת אינטגרציה חשובה: רינדור מיילים עבר ל-service נפרד `email-renderer` (Node.js + Express + React Email) בצד הבקאנד/worker. לפרונט אין תלות ישירה בשירות זה, אך שינויי נוסח/תוכן מיילים מנוהלים עכשיו ב-`email-renderer/src/emails/templates/` ולא ב-Jinja בבקאנד.

## Stack

- **React 19** + **TypeScript** + **Vite 7**
- **React Router** for routing
- **Axios** HTTP client with interceptors in [`src/api/client.ts`](../src/api/client.ts)
- **Firebase** for FCM (see `FCMCheck`, notifications)
- Styling: **CSS Modules** (`.module.css`) per page/component; body font via **`var(--font-primary)`** / numeric via **`var(--font-numeric)`** (set by [`LangContext`](../src/context/LangContext.tsx))
- **i18n:** **i18next** — `src/i18n/locales/{he,en}/`; [`utils/date.ts`](../src/utils/date.ts) + **`getLocale()`** for locale-aware dates; [`utils/i18nError.ts`](../src/utils/i18nError.ts) **`apiErr`** for translated `getApiErrorMessage` fallbacks in hooks — see [`docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md`](../../docs/adr/ARCHITECTURE_DECISIONS_FRONTEND.md) §10–12

## Directory layout

| Area | Path | Role |
|------|------|------|
| API surface | `src/api/` | Thin wrappers around `api` in [`client.ts`](../src/api/client.ts): `auth.ts`, `chat.ts`, `passengers.ts`, `presence.ts`, `rides.ts`, `bookings.ts`, `geo.ts`, `users.ts`, `groups.ts`. ייבוא `api` ישיר מ־`client` רק בשכבה זו, ב־[`AuthContext`](../src/context/AuthContext.tsx) (טוקנים), וב־[`api/presence.ts`](../src/api/presence.ts) (`chatWsApi`). |
| App shell | `src/components/Layout/` | Nav, outlet, global UI; shell logic in [`useLayoutShell.ts`](../src/components/Layout/useLayoutShell.ts) (`formatNavBadge` על ספירות מ־`ChatContext` — תגית מספרית על אייקון הודעות/התראות; כשיש ספירה, נוספת מחלקה **`.iconBtnUnread`** ב־[`Layout.module.css`](../src/components/Layout/Layout.module.css) עם טוקני **primary** / **primary-light** / **primary-soft-border** כמו כפתור החיפוש). Profile menu, **“הפעל התראות”** → `initFCM`, chat popup visibility. **FCM after login** lives in [`AuthContext`](../src/context/AuthContext.tsx) (`initFCM` / `cleanupFCM` + `patchFcmToken(null)` on logout). |
| Chat popup | `src/components/ChatPopup/` | Floating thread UI; data/side-effects in [`useChatPopup.ts`](../src/components/ChatPopup/useChatPopup.ts) — אותה שכבת idempotency outbound + dedupe כמו ב-thread |
| Pages | `src/pages/` | Route screens; heavier flows use colocated hooks (e.g. `useCreateRide.ts`, `useProfile.ts`, `useFCMCheck.ts`) and small `*.utils.ts` where useful (e.g. `MyBookings/myBookings.utils.ts`). **חיפוש נסיעות (נוסע):** [`SearchRides/index.tsx`](../src/pages/SearchRides/index.tsx) + [`useSearchRides.ts`](../src/pages/SearchRides/useSearchRides.ts) (`buildManualRideSearchParams`, `buildParamsFromAiResult`, `searchMode` — `date_only` / `datetime` / `time_range`) + [`useJoinRide.ts`](../src/pages/SearchRides/useJoinRide.ts) (הצטרפות מחיפוש + **Idempotency-Key** ב־`useRef`) — `GET …/passengers/search-rides`; **שמירת התראה** דרך [`saveSearchAlert`](../src/api/passengers.ts) → `POST …/passengers/`; מצב `hasSearched` כדי להפריד בין טופס ריק לבין “אין תוצאות אחרי חיפוש”; מסך **התראות** — לוגיקת תצוגה וקיבוץ ב־[`Notifications.tsx`](../src/pages/Notifications.tsx) (ללא hook נפרד). ניהול קבוצה: קומפוזיציה ב־[`useGroupManage.ts`](../src/pages/GroupManage/useGroupManage.ts) מ־[`useGroupManageLists.ts`](../src/pages/GroupManage/useGroupManageLists.ts), [`useGroupManageHeader.ts`](../src/pages/GroupManage/useGroupManageHeader.ts), [`useGroupManageInvite.ts`](../src/pages/GroupManage/useGroupManageInvite.ts), [`useGroupManageMutations.ts`](../src/pages/GroupManage/useGroupManageMutations.ts). **הזמנות שלי** ([`MyBookings/`](../src/pages/MyBookings/)): נתונים ב־[`fetchDriverSummary`](../src/api/bookings.ts) / [`fetchPassengerSummary`](../src/api/bookings.ts) (REST מאוגד); נוסע — [`useMyBookingsPassenger.ts`](../src/pages/MyBookings/useMyBookingsPassenger.ts), נהג — [`useMyBookingsDriver.ts`](../src/pages/MyBookings/useMyBookingsDriver.ts); VM מקונן ב־[`useMyBookings.ts`](../src/pages/MyBookings/useMyBookings.ts) (`passenger`, `driver`, `chat`) + **`MyBookingsViewModel`**; מיפוי DTO מרוכז ב־[`myBookings.mappers.ts`](../src/pages/MyBookings/myBookings.mappers.ts); כרטיס נוסע — [`PassengerBookingCard.tsx`](../src/pages/MyBookings/PassengerBookingCard.tsx); כניסה למסך — [`index.tsx`](../src/pages/MyBookings/index.tsx). |
| Message thread | `src/pages/MessageThread/` | רשימת הודעות: **`ChatListRow[]`** ([`types/chatList.ts`](../src/types/chatList.ts)) — **`confirmed`** / **`pending`**; מיזוג **`applyInboundRealMessage`** + **`appendMessageDedupById`** ([`chatMessagesMerge.ts`](../src/utils/chatMessagesMerge.ts)) מ־REST, WS, ו־rollback. [`processChatWebSocketMessage.ts`](../src/pages/MessageThread/processChatWebSocketMessage.ts) + **`outboundPendingRef`**; [`useChatWebSocket.ts`](../src/pages/MessageThread/useChatWebSocket.ts) — ping/typing, **`onopen`** → **`fetchMissedMessages(lastMessageIdRef ?? 0)`**, reconnect delay — [`reconnectBackoff.ts`](../src/utils/reconnectBackoff.ts). [`fetchMissedGap.ts`](../src/pages/MessageThread/fetchMissedGap.ts) — השלמת פער reconnect: **`after`** אז **`before=next_cursor`** (עם מכסה ו־retry). [`useConversationMessages.ts`](../src/pages/MessageThread/useConversationMessages.ts) — **`lastMessageIdRef`** = max **`message_id`** על שורות **confirmed** בלבד; **`fetchMissedMessages`** (דרך **`fetchMissedGap`**) שומר זנב **pending** וביטול עם **`cidRef`** אם מתחלפת השיחה. [`useMessageThread.ts`](../src/pages/MessageThread/useMessageThread.ts) — optimistic send + **`outboundIdempotencyKey`**. בדיקות: [`processChatWebSocketMessage.test.ts`](../src/pages/MessageThread/processChatWebSocketMessage.test.ts), [`fetchMissedGap.test.ts`](../src/pages/MessageThread/fetchMissedGap.test.ts), [`chatMessagesMerge.test.ts`](../src/utils/chatMessagesMerge.test.ts). חוזי JSON ל-WS (נסיעות, מיקום, צ’אט): [`docs/architecture/REALTIME.md`](../../docs/architecture/REALTIME.md). |
| Google Sign-In | `src/components/GoogleSignIn/` | טעינת סקריפט GIS ב־[`useGoogleSignInScript.ts`](../src/components/GoogleSignIn/useGoogleSignInScript.ts); [`useGoogleSignIn.ts`](../src/components/GoogleSignIn/useGoogleSignIn.ts) מאחד credential + render כפתור. |
| Context | `src/context/` | Auth, groups, chat, **`LangContext`** (שפה, `dir`, `--font-primary`); מצב סינכרוני של צ'אט/התראות ב־[`chatState.ts`](../src/context/chatState.ts) + `chatReducer`. [`ChatContext.tsx`](../src/context/ChatContext.tsx) מרכיב: [`useChatOpenClose.ts`](../src/context/useChatOpenClose.ts), [`useChatUnreadMessages.ts`](../src/context/useChatUnreadMessages.ts) (**`setUnreadDirect`**), [`useChatNotificationsFeed.ts`](../src/context/useChatNotificationsFeed.ts) (REST **~5 דקות** polling), **`useUserEventStream`** (**`InvalidateEvent`** ראשון, אחר כך **`UserEvent`**) על **`user:{id}:events`**: **`handleInvalidate`** ל־באדג'ים (**`notifications`** מפעיל גם **`NOTIFICATIONS_REFRESH_EVENT`** + **`linkup:user-event`** מותנה); פריימי **`unread_count`** בערוץ צ'אט — עדיין דרך **`processChatWebSocketMessage`** / **`ChatPresenceEventSchema`**; מאזין יחיד כאן, לא ב-Layout; טיפוסי ערך ב־[`chatContext.types.ts`](../src/context/chatContext.types.ts). |
| Shared hooks | `src/hooks/` | Reusable behavior; live GPS: `useLocationBroadcast`, `usePassengerLocationBroadcast`, `useLocationWatcher`, `useDriverLocation`, `usePassengerLocations`, `useMapMarker` (see `docs/architecture/REALTIME.md`) |
| Types | `src/types/` | Shared TS types (e.g. `Ride`); **Chat list rows:** [`chatList.ts`](../src/types/chatList.ts) (**`ChatListRow`**); **WebSocket ingress:** [`wsEvents.ts`](../src/types/wsEvents.ts) (Zod: ride / location / chat presence) |
| Utils | `src/utils/` | Pure helpers: `apiError` (כולל **`isChatIdempotencyKeyMismatch`**), **`i18nError` (`apiErr`)**, **`date` + `getLocale`**, **`chatMessagesMerge`** (`appendMessageDedupById`, **`applyInboundRealMessage`**, **`removePendingByClientId`**), **`outboundIdempotencyKey`**, **`reconnectBackoff`** — **`computeReconnectDelayMs(attempt, { baseMs?, maxMs?, jitterRatio? })`**: ברירת מחדל בסיס **3s**, תקרה **30s**, jitter **±20%**; משותף ל־**`useChatWebSocket`**, **`useReconnectingWebSocket`**, **`useReconnectingWebSocketState`** (Vitest: `reconnectBackoff.test.ts`), `rideDisplay`, וכו'. |
| Shared UI | `src/components/ErrorBanner/`, `LoadingButton/`, `RouteErrorBoundary/` | `ErrorBanner` עם `variant="compact"` לשורות צרות (הזמנה, מפה, סרגל); כפתור טעינה; `RouteErrorBoundary` ב־[`App.tsx`](../src/App.tsx) |
| Config | `src/config/` | Env-derived URLs and keys |
| Design tokens | [`src/styles/tokens.css`](../src/styles/tokens.css) | משתני CSS (בהיר/כהה), ריווחים ורדיוסים; `html[data-theme]`; [`ThemeContext`](../src/context/ThemeContext.tsx) + [`ThemeToggle`](../src/components/ThemeToggle/ThemeToggle.tsx) |

## Data flow

1. **Auth**: `AuthContext` stores user + tokens; **`tearDownSession({ reason })`** unifies logout, bootstrap failure, and refresh failure teardowns; `client.ts` emits **`auth:session-expired`** after **`clearTokens`** on failed/absent refresh (listener in `AuthContext`). `api/client` attaches `Authorization` and retries once on **401** via refresh queue; React Query **`captureExceptionOnce`** skips Sentry only for **401**. See **`docs/FEATURE_DECISIONS.md`** (`#auth-session-teardown`) and **ADR Frontend §21**.
2. **REST**: Prefer calling functions from `src/api/*.ts` instead of raw paths in components (easier to grep and type).
3. **Realtime**: WebSockets where needed (e.g. ride list updates in `MyRides`), separate from REST base URL (`config/env`). Incoming frames validated with **Zod** (`safeParse`) via [`wsEvents.ts`](../src/types/wsEvents.ts). Human-readable contracts: [`REALTIME.md`](../../docs/architecture/REALTIME.md).

## Error handling

- User-facing messages: [`getApiErrorMessage`](../src/utils/apiError.ts) is the single source of truth for Axios/FastAPI `detail` / `message` normalization; [`getApiStatus`](../src/utils/apiError.ts) / `getApiErrorCode` / `isTimeoutOrAbortError` / **`isChatIdempotencyKeyMismatch`** לענפי לוגיקה (סטטוסים, timeout, צ’אט 422).
- Unit tests: `src/utils/apiError.test.ts`, `src/utils/chatMessagesMerge.test.ts` (`npm run test`).

## Security (XSS + browser CSP)

- **In-app:** avoid raw HTML; **`react/no-danger`** is enforced; use **`sanitizeHtml()`** from [`utils/sanitize.ts`](../src/utils/sanitize.ts) when rich text is required.
- **Edge (production Compose):** enforcing **`Content-Security-Policy`** is defined in **`nginx/nginx.conf.template`** and rendered to **`nginx/nginx.conf`** via **`scripts/ops/render-nginx-conf.sh`** (local) or CI deploy (**`SENTRY_REPORT_URI`** in **`backend/.env`**); not in Vite. The build is a **static SPA** (no SSR), so future **nonce**-based CSP tightening needs edge HTML rewriting or hashes — see **[`docs/SECURITY_HEADERS.md`](../../docs/SECURITY_HEADERS.md)** and **[`docs/FEATURE_DECISIONS.md`](../../docs/FEATURE_DECISIONS.md#browser-csp-edge)**.
- **API:** chat messages are **plaintext-only** with server-side HTML rejection — **[`docs/FEATURE_DECISIONS.md`](../../docs/FEATURE_DECISIONS.md#chat-plaintext)**.

## Conventions

- New endpoints: add a function in the appropriate `src/api/<domain>.ts` file and import it from pages/hooks.
- New pages: default export from `pages/<Name>.tsx` or `pages/<Name>/index.tsx`; register route in `App.tsx`.
- **UI copy:** prefer **`useTranslation`** + JSON namespaces under `src/i18n/locales/`; for hook-level API error fallbacks use **`apiErr('err_*')`** with keys in `common.json`. Keep server-driven `error_code` handling aligned with [`docs/ERRORS.md`](../../docs/ERRORS.md).

## Scripts

- `npm run dev` – dev server (proxies `/api/v1`, `/ws`, `/presence` per `vite.config.ts`)
- `npm run build` – `tsc -b` + Vite build
- `npm run lint` – ESLint
- `npm run test` – Vitest (node environment)

## מבחני עומס (k6)

עומס על **auth בבקאנד** (לא על הפרונט ישירות): מקור אמת **`backend/k6/scripts/load_test_auth.js`**; **`backend/load_test.js`** הוא wrapper תואם לאחור — ראו `backend/README.md` ו־`docs/ENGINEERING_HIGHLIGHTS.md`. הפרונט בפיתוח משתמש ב-proxy ל־API; ודאו שה-backend רץ לפני הרצת k6.
