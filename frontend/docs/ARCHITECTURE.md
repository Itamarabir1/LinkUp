# Frontend architecture (Linkup)

רשימת ריפקטור ואיכות מלאה (מקור אמת): [`FRONTEND_REFACTOR_AND_QUALITY.md`](./FRONTEND_REFACTOR_AND_QUALITY.md). סיכום להצגה בפורטפוליו: [`../../docs/ENGINEERING_HIGHLIGHTS.md`](../../docs/ENGINEERING_HIGHLIGHTS.md) (סעיף 14).

## Stack

- **React 19** + **TypeScript** + **Vite 7**
- **React Router** for routing
- **Axios** HTTP client with interceptors in [`src/api/client.ts`](../src/api/client.ts)
- **Firebase** for FCM (see `FCMCheck`, notifications)
- Styling: **CSS Modules** (`.module.css`) per page/component

## Directory layout

| Area | Path | Role |
|------|------|------|
| API surface | `src/api/` | Thin wrappers around `api` in [`client.ts`](../src/api/client.ts): `auth.ts`, `chat.ts`, `passengers.ts`, `presence.ts`, `rides.ts`, `bookings.ts`, `geo.ts`, `users.ts`, `groups.ts`. ייבוא `api` ישיר מ־`client` רק בשכבה זו, ב־[`AuthContext`](../src/context/AuthContext.tsx) (טוקנים), וב־[`api/presence.ts`](../src/api/presence.ts) (`chatWsApi`). |
| App shell | `src/components/Layout/` | Nav, outlet, global UI; shell logic in [`useLayoutShell.ts`](../src/components/Layout/useLayoutShell.ts) (profile menu, **“הפעל התראות”** → `initFCM`, chat popup visibility). **FCM after login** lives in [`AuthContext`](../src/context/AuthContext.tsx) (`initFCM` / `cleanupFCM` + `patchFcmToken(null)` on logout). |
| Chat popup | `src/components/ChatPopup/` | Floating thread UI; data/side-effects in [`useChatPopup.ts`](../src/components/ChatPopup/useChatPopup.ts) |
| Pages | `src/pages/` | Route screens; heavier flows use colocated hooks (e.g. `useCreateRide.ts`, `useProfile.ts`, `useFCMCheck.ts`) and small `*.utils.ts` where useful (e.g. `MyBookings/myBookings.utils.ts`). מסך **התראות** — לוגיקת תצוגה וקיבוץ ב־[`Notifications.tsx`](../src/pages/Notifications.tsx) (ללא hook נפרד). ניהול קבוצה: קומפוזיציה ב־[`useGroupManage.ts`](../src/pages/GroupManage/useGroupManage.ts) מ־[`useGroupManageLists.ts`](../src/pages/GroupManage/useGroupManageLists.ts), [`useGroupManageHeader.ts`](../src/pages/GroupManage/useGroupManageHeader.ts), [`useGroupManageInvite.ts`](../src/pages/GroupManage/useGroupManageInvite.ts), [`useGroupManageMutations.ts`](../src/pages/GroupManage/useGroupManageMutations.ts). **הזמנות שלי**: נוסע ב־[`useMyBookingsPassenger.ts`](../src/pages/MyBookings/useMyBookingsPassenger.ts), נהג ב־[`useMyBookingsDriver.ts`](../src/pages/MyBookings/useMyBookingsDriver.ts), קומפוזיציה ב־[`useMyBookings.ts`](../src/pages/MyBookings/useMyBookings.ts) — return **מפורש** (מיפוי שדה-שדה), בלי `...passenger` / `...driver`, כדי שחוזה ה-view-model ל־[`index.tsx`](../src/pages/MyBookings/index.tsx) יהיה קריא במקום אחד. |
| Message thread | `src/pages/MessageThread/` | עיבוד הודעות WS ב־[`processChatWebSocketMessage.ts`](../src/pages/MessageThread/processChatWebSocketMessage.ts); [`useChatWebSocket.ts`](../src/pages/MessageThread/useChatWebSocket.ts) מחבר ומנהל ping/typing. בדיקות: [`processChatWebSocketMessage.test.ts`](../src/pages/MessageThread/processChatWebSocketMessage.test.ts) — אירועי typing עם `conversation_id` / `recipient_id` כמו ב־chat-ws. חוזי JSON ל-WS (נסיעות, מיקום, צ’אט): [`docs/architecture/REALTIME.md`](../../docs/architecture/REALTIME.md). |
| Google Sign-In | `src/components/GoogleSignIn/` | טעינת סקריפט GIS ב־[`useGoogleSignInScript.ts`](../src/components/GoogleSignIn/useGoogleSignInScript.ts); [`useGoogleSignIn.ts`](../src/components/GoogleSignIn/useGoogleSignIn.ts) מאחד credential + render כפתור. |
| Context | `src/context/` | Auth, groups, chat; מצב סינכרוני של צ'אט/התראות ב־[`chatState.ts`](../src/context/chatState.ts) + `chatReducer`. [`ChatContext.tsx`](../src/context/ChatContext.tsx) מרכיב: [`useChatOpenClose.ts`](../src/context/useChatOpenClose.ts), [`useChatUnreadMessages.ts`](../src/context/useChatUnreadMessages.ts), [`useChatNotificationsFeed.ts`](../src/context/useChatNotificationsFeed.ts), [`useChatNotificationsWebSocket.ts`](../src/context/useChatNotificationsWebSocket.ts); טיפוסי ערך ב־[`chatContext.types.ts`](../src/context/chatContext.types.ts). |
| Shared hooks | `src/hooks/` | Reusable behavior; live GPS: `useLocationBroadcast`, `usePassengerLocationBroadcast`, `useLocationWatcher`, `useDriverLocation`, `usePassengerLocations`, `useMapMarker` (see `docs/architecture/REALTIME.md`) |
| Types | `src/types/` | Shared TS types (e.g. `Ride`); **WebSocket ingress:** [`wsEvents.ts`](../src/types/wsEvents.ts) (Zod: ride / location / chat presence) |
| Utils | `src/utils/` | Pure helpers (`apiError`, `rideDisplay` לתווית מקור נסיעה, dates, etc.) |
| Shared UI | `src/components/ErrorBanner/`, `LoadingButton/`, `RouteErrorBoundary/` | `ErrorBanner` עם `variant="compact"` לשורות צרות (הזמנה, מפה, סרגל); כפתור טעינה; `RouteErrorBoundary` ב־[`App.tsx`](../src/App.tsx) |
| Config | `src/config/` | Env-derived URLs and keys |
| Design tokens | [`src/styles/tokens.css`](../src/styles/tokens.css) | משתני CSS (בהיר/כהה), ריווחים ורדיוסים; `html[data-theme]`; [`ThemeContext`](../src/context/ThemeContext.tsx) + [`ThemeToggle`](../src/components/ThemeToggle/ThemeToggle.tsx) |

## Data flow

1. **Auth**: `AuthContext` stores user + tokens; `api/client` attaches `Authorization` and refreshes on 401 when possible.
2. **REST**: Prefer calling functions from `src/api/*.ts` instead of raw paths in components (easier to grep and type).
3. **Realtime**: WebSockets where needed (e.g. ride list updates in `MyRides`), separate from REST base URL (`config/env`). Incoming frames validated with **Zod** (`safeParse`) via [`wsEvents.ts`](../src/types/wsEvents.ts). Human-readable contracts: [`REALTIME.md`](../../docs/architecture/REALTIME.md).

## Error handling

- User-facing messages: [`getApiErrorMessage`](../src/utils/apiError.ts) normalizes Axios/FastAPI `detail` / `message` shapes; [`getApiStatus`](../src/utils/apiError.ts) / `getApiErrorCode` / `isTimeoutOrAbortError` לענפי לוגיקה (סטטוסים, timeout).
- Unit tests: `src/utils/apiError.test.ts` (`npm run test`).

## Conventions

- New endpoints: add a function in the appropriate `src/api/<domain>.ts` file and import it from pages/hooks.
- New pages: default export from `pages/<Name>.tsx` or `pages/<Name>/index.tsx`; register route in `App.tsx`.
- Hebrew UI copy lives inline in components; keep error strings consistent with backend codes when applicable.

## Scripts

- `npm run dev` – dev server (proxies `/api/v1`, `/ws`, `/presence` per `vite.config.ts`)
- `npm run build` – `tsc -b` + Vite build
- `npm run lint` – ESLint
- `npm run test` – Vitest (node environment)

## מבחני עומס (k6)

עומס על **auth בבקאנד** (לא על הפרונט ישירות): סקריפט בשורש הפרויקט **`backend/load_test.js`** — ראו `backend/README.md` ו־`docs/ENGINEERING_HIGHLIGHTS.md`. הפרונט בפיתוח משתמש ב-proxy ל־API; ודאו שה-backend רץ לפני הרצת k6.
