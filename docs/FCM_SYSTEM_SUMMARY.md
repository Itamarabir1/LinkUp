# LinkUp FCM End-to-End Summary

This document summarizes the Firebase Cloud Messaging (FCM) implementation in LinkUp across frontend and backend: token registration, **server payloads that use the FCM `data` map only** (no top-level `notification` field from our backend), service worker handling, and foreground UX (**in-app toast + chime**).

**Terminology:** “**Data-only**” here means the **Firebase Admin message** we send has **`data`** (string key/value) and **does not** set FCM’s separate `notification` block. That is **not** “no UI”: the app still shows a **popup toast** and **sound** when the tab is in the foreground, and the service worker shows a **system notification** when the app is in the background.

## 1) High-Level Architecture

FCM delivery has two connected paths:

1. **Token registration (frontend → backend → DB)**
   - Browser requests notification permission, registers the Firebase messaging service worker, obtains an FCM token (VAPID).
   - Frontend sends the token to the backend: `PATCH /api/v1/users/fcm-token`.
   - Backend stores it on `users.fcm_token`.

2. **Notification dispatch (business event → worker → Firebase → browser)**
   - A domain event is written to the outbox (e.g. `booking.passenger_join_request`).
   - `outbox-worker` consumes the event and builds notification context.
   - The notification manager dispatches channels (`email`, `push`, `websocket`) per event strategy.
   - The push provider uses Firebase Admin SDK to send an FCM message to the stored token.
   - **Payload shape:** the backend sends a **data-only** message (`title` and `body` as string entries in `data`, plus optional extra string fields). This avoids the client auto-display path that only fires for `notification` payloads and keeps display logic under our control.
   - **Browser UX:**
     - **Background / closed tab:** the service worker handles the **`push`** event, parses FCM JSON, reads `data.title` / `data.body`, and calls `registration.showNotification(...)` (system notification).
     - **Foreground (tab focused):** Firebase delivers the message to `onMessage` in the app; the UI shows an **in-app toast** (WhatsApp Web–style) plus optional chime — not a second competing system notification for the same flow.

## 2) Frontend Flow (Web FCM)

### 2.1 Initialization trigger

- **`AuthContext`** ([`frontend/src/context/AuthContext.tsx`](frontend/src/context/AuthContext.tsx)): after successful **password login**, **Google sign-in**, or **initial session hydrate** (`fetchCurrentUser`), if `Notification.permission === 'granted'`, the app calls `void initFCM()` so the backend receives a fresh token for the logged-in user.
- **Logout order:** `PATCH /users/fcm-token` with `{ "fcm_token": null }` (while the access token is still valid), then **`cleanupFCM()`** (unsubscribes foreground `onMessage`), then server `logout` / local token clear — so push is not sent to a stale device registration after sign-out.
- **Profile menu:** “הפעל התראות” / enable notifications — [`useLayoutShell.ts`](frontend/src/components/Layout/useLayoutShell.ts) calls `initFCM()` on user action (permission prompt + registration).
- **Debug:** [`frontend/src/pages/FCMCheck.tsx`](frontend/src/pages/FCMCheck.tsx) can call `initFCM()` manually.

### 2.2 What `initFCM()` does

- File: [`frontend/src/services/fcm.ts`](frontend/src/services/fcm.ts)
- Steps:
  1. Check browser support (`Notification`, `serviceWorker`).
  2. Request notification permission (if not already decided).
  3. Register service worker `/firebase-messaging-sw.js`.
  4. Firebase config for the SW is **baked into** `firebase-messaging-sw.js` (no `postMessage` from the app).
  5. Get messaging instance (`getMessagingSafe()` from [`frontend/src/config/firebase.ts`](frontend/src/config/firebase.ts)).
  6. Register **foreground** listener `onMessage` once (module-level guard).
  7. `getToken` with VAPID key and the same SW registration.
  8. `PATCH /users/fcm-token` with `{ "fcm_token": "<token>" }` (or `{ "fcm_token": null }` on logout to clear `users.fcm_token` in the DB).

### 2.3 Foreground vs background

- **Background**
  - File: [`frontend/public/firebase-messaging-sw.js`](frontend/public/firebase-messaging-sw.js)
  - **`push` listener:** `event.waitUntil(registration.showNotification(...))` using `title` / `body` from `event.data?.json()?.data` (matches data-only backend).
  - **`messaging.onBackgroundMessage`:** still present for compatibility / `notification`-style payloads (e.g. `vibrate` on supported platforms). With **data-only** sends from the backend, the primary display path for system notifications is the **`push` handler**.

- **Foreground**
  - File: [`frontend/src/services/fcm.ts`](frontend/src/services/fcm.ts)
  - `onMessage` → `showForegroundNotification`:
    - [`triggerNotificationToast`](frontend/src/components/NotificationToast/NotificationToast.tsx) — fixed toast at top of app (mounted in Layout).
    - [`playNotificationChime`](frontend/src/utils/notificationSound.ts) — optional sound (subject to browser autoplay rules).
  - Title/body are taken from **`payload.data.title` / `payload.data.body`** first, then fall back to `payload.notification` if the SDK surfaces them — see [`frontend/src/services/fcm.ts`](frontend/src/services/fcm.ts) (`showForegroundNotification`).

### 2.4 In-app toast shell

- Component: [`frontend/src/components/NotificationToast/NotificationToast.tsx`](frontend/src/components/NotificationToast/NotificationToast.tsx) + CSS module; **mounted once in** [`App.tsx`](frontend/src/App.tsx) (not inside `Layout` / `AdminLayout`).
- Exported `triggerNotificationToast({ title, body })` from [`notificationToast.utils.ts`](frontend/src/components/NotificationToast/notificationToast.utils.ts) sets global toast state; auto-dismiss ~5s and manual close.

### 2.5 Firebase config (Vite env)

- File: [`frontend/src/config/firebase.ts`](frontend/src/config/firebase.ts)
- Env vars (see [`frontend/.env.example`](frontend/.env.example)):
  - `VITE_FIREBASE_*` (apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId, measurementId)
  - `VITE_FIREBASE_VAPID_KEY` — required for `getToken` on web.

### 2.6 Dev test UI

- [`frontend/src/pages/FCMCheck.tsx`](frontend/src/pages/FCMCheck.tsx) — permission, token, server registration, foreground logging.

## 3) Backend Flow (Token + Push)

### 3.1 Token API

- Route: [`backend/app/domain/users/router.py`](../backend/app/domain/users/router.py) — `PATCH /users/fcm-token` (mounted under `/api/v1/users` via [`api_router.py`](../backend/app/api/v1/api_router.py)).
- Body: `FCMTokenUpdate` — `fcm_token` may be a string or **`null`** to clear the stored token (logout / device change).
- Persistence: `update_fcm_token` in users service/CRUD; column `users.fcm_token` (nullable).

### 3.2 Outbox → worker → push

- Mappings: [`backend/app/domain/notifications/config/mappings.py`](backend/app/domain/notifications/config/mappings.py)
- Worker: [`backend/app/workers/main_worker.py`](backend/app/workers/main_worker.py), [`backend/app/workers/tasks/notification_tasks.py`](backend/app/workers/tasks/notification_tasks.py)
- Orchestration: [`backend/app/domain/notifications/core/handler.py`](backend/app/domain/notifications/core/handler.py), [`manager.py`](backend/app/domain/notifications/manager.py)

### 3.3 FCM client (server: `data` map only)

- File: [`backend/app/domain/notifications/channels/push/client.py`](backend/app/domain/notifications/channels/push/client.py)
- Builds `firebase_admin.messaging.Message` with **`data` only** (all values must be strings per FCM):

```python
messaging.Message(
    data={
        "title": title,
        "body": body,
        **{k: str(v) for k, v in (data or {}).items()},
    },
    token=token,
)
```

- No top-level `notification` field — intentional for the web behavior described above.

### 3.4 Firebase Admin init

- [`backend/app/infrastructure/firebase_core/firebase.py`](backend/app/infrastructure/firebase_core/firebase.py) — `FIREBASE_CREDENTIALS_JSON` or `FIREBASE_SERVICE_ACCOUNT_PATH`
- The **outbox-worker** loads the same module when handling push; it must see valid credentials in every environment where FCM is used.

### 3.5 Docker Compose — credentials on disk

- The service account JSON is **not** baked into the image (see `backend/.dockerignore`). At runtime, Compose mounts the host file into **both** `backend` and `outbox-worker`:

  `backend/app/infrastructure/firebase_core/firebase-credentials.json` → `/app/infrastructure/firebase_core/firebase-credentials.json` (read-only)

- Set in `backend/.env` (used by both services via `env_file`):

  `FIREBASE_SERVICE_ACCOUNT_PATH=/app/infrastructure/firebase_core/firebase-credentials.json`

- Without this mount + path, push from the worker can fail with Firebase Admin errors such as “The default Firebase app does not exist.”

## 4) Example Sequence (e.g. passenger join request)

1. Passenger triggers join request; outbox event `booking.passenger_join_request`.
2. Worker resolves driver and strategy including `push`.
3. `PushProvider` checks `driver.fcm_token`.
4. `FCMClient.send` uses the **`data` map only** at the FCM API (`title`, `body`, optional metadata strings).
5. Driver browser:
   - Tab in background: SW **`push`** → system notification.
   - Tab focused: `onMessage` → **toast** + chime.

## 5) Operational Notes

1. **Dev:** seeing `http://localhost:5173/api/v1/...` in the network tab is normal — Vite proxies `/api` to the backend.
2. **Token saved ≠ delivery:** token must be valid and permission granted.
3. **Skip push:** missing/invalid `fcm_token` — provider skips or logs.
4. **Duplicate notifications:** if both raw `push` and `onBackgroundMessage` run for the same message, you could see double system notifications; current design prioritizes **`push`** for data-only; trim `onBackgroundMessage` if duplicates appear.
5. **Permissions:** site notifications must be **Allow** for token + SW display.

## 6) File Inventory (FCM-related)

| Area | Files |
|------|--------|
| Frontend FCM | `frontend/src/services/fcm.ts` (`initFCM`, **`cleanupFCM`**), `frontend/src/config/firebase.ts`, `frontend/public/firebase-messaging-sw.js` |
| Toast UI | `NotificationToast.tsx`, `.module.css`, **`App.tsx`** (mount), `notificationToast.utils.ts` |
| Auth + token lifecycle | `frontend/src/context/AuthContext.tsx`, `frontend/src/api/users.ts` (`patchFcmToken`) |
| Profile “enable notifications” | `frontend/src/components/Layout/useLayoutShell.ts` |
| Debug | `frontend/src/pages/FCMCheck.tsx`, `frontend/src/utils/notificationSound.ts` |
| Backend push | `backend/app/domain/notifications/channels/push/client.py`, `render.py`, `push_provider.py` |
| Firebase admin | `backend/app/infrastructure/firebase_core/firebase.py` |
| User token API | `backend/app/domain/users/router.py`, schema `FCMTokenUpdate`, service/crud/model |

## 7) Quick Validation Checklist

1. Browser: permission granted, SW registered, token obtained (FCMCheck or logs).
2. `PATCH /api/v1/users/fcm-token` returns 200.
3. Worker logs: `Push sent successfully` or explicit skip (no token / invalid).
4. Trigger a push event:
   - **Background:** system notification from SW (`push` handler).
   - **Foreground:** toast under app chrome + sound if allowed.

## 8) Scheduled email reminders (ReminderScheduler → handler)

`ReminderScheduler` calls `NotificationHandler.handle_event` with an in-process payload (not the outbox). **Contract:** `scheduled_notification_id`, `ride_id`, and `user_id` together identify a due row in `scheduled_notifications` and tell the handler to hydrate a **`ScheduledReminderSource`**: the **ride** (with driver) supplies template context (`RideBuilder`); **`user_id`** is the recipient. Without all three fields, `ride_id` alone still loads a bare `Ride` and the usual resolver/builder paths apply. See [`backend/app/domain/notifications/core/scheduled_reminder_source.py`](../backend/app/domain/notifications/core/scheduled_reminder_source.py).

## 9) Related docs

- [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) — portfolio summary (includes FCM).
- [`docs/architecture/API.md`](architecture/API.md) — `PATCH /fcm-token`.
- [`docs/architecture/EVENTS.md`](architecture/EVENTS.md) — notifications queue.
