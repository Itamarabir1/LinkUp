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
   - **`notification-worker`** reads **`outbox_events`**, publishes to RabbitMQ, consumes **`notifications_queue`**, and builds notification context (see [`architecture/NOTIFICATIONS.md`](architecture/NOTIFICATIONS.md)).
   - The notification manager dispatches channels (`email`, `push`, `websocket`) per event strategy.
   - The push provider uses Firebase Admin SDK to send an FCM message to the stored token.
   - **Payload shape:** the backend sends a **data-only** message (`title` and `body` as string entries in `data`, plus optional extra string fields). This avoids the client auto-display path that only fires for `notification` payloads and keeps display logic under our control.
   - **Browser UX:**
     - **Background / closed tab:** the service worker handles the **`push`** event, parses FCM JSON, reads `data.title` / `data.body`, and calls `registration.showNotification(...)` (system notification).
     - **Foreground (tab focused):** Firebase delivers the message to `onMessage` in the app; the UI shows an **in-app toast** (WhatsApp Web–style) plus optional chime — not a second competing system notification for the same flow.

## 2) Frontend Flow (Web FCM)

### 2.1 Initialization trigger

- **`AuthContext`** ([`frontend/src/context/AuthContext.tsx`](../frontend/src/context/AuthContext.tsx)): after successful **password login**, **Google sign-in**, or **initial session hydrate** (`fetchCurrentUser`), the app calls `void initFCM()` unconditionally so the backend receives a fresh token for the logged-in user. `initFCM()` itself handles permission state internally (requests permission if `"default"`, exits early if `"denied"` or unsupported).
- **Logout order (explicit user sign-out — `tearDownSession({ reason: 'user-action' })`):** `PATCH /users/fcm-token` with `{ "fcm_token": null }` (while the access token is still valid), then **`cleanupFCM()`** (unsubscribes foreground `onMessage`), then server `logout` / local token clear — so push is not sent to a stale device registration after sign-out.
- **Session expiry / refresh failure (`session-expired`):** teardown clears tokens and local FCM listeners via the same **`cleanupFCM`** path but **does not** call **`PATCH …/fcm-token`** — intentional to avoid chained **401**s when JWT is already invalid; DB token can be refreshed on next successful login ([`FEATURE_DECISIONS.md`](FEATURE_DECISIONS.md#auth-session-teardown)).
- **Profile menu:** “הפעל התראות” / enable notifications — [`useLayoutShell.ts`](../frontend/src/components/Layout/useLayoutShell.ts) calls `initFCM()` on user action (permission prompt + registration).
- **Debug:** [`frontend/src/pages/FCMCheck.tsx`](../frontend/src/pages/FCMCheck.tsx) can call `initFCM()` manually.

### 2.2 What `initFCM()` does

- File: [`frontend/src/services/fcm.ts`](../frontend/src/services/fcm.ts)
- Steps:
  1. Check browser support (`Notification`, `serviceWorker`).
  2. Request notification permission (if not already decided).
  3. Register service worker `/firebase-messaging-sw.js`.
  4. Firebase config for the SW is **baked into** `firebase-messaging-sw.js` (no `postMessage` from the app).
  5. Get messaging instance (`getMessagingSafe()` from [`frontend/src/config/firebase.ts`](../frontend/src/config/firebase.ts)).
  6. Register **foreground** listener `onMessage` once (module-level guard).
  7. `getToken` with VAPID key and the same SW registration.
  8. **localStorage cache check:** compares the new token against `localStorage('fcm_token')`; if unchanged, skips the PATCH (avoids a redundant backend call on every page reload when the token hasn't rotated). On change: `PATCH /users/fcm-token` with `{ "fcm_token": "<token>" }` and updates the cache. On logout / session teardown: `cleanupFCM()` clears the cached key so the next user always sends their token. (Or `{ "fcm_token": null }` on explicit logout to clear `users.fcm_token` in the DB.)

- **Logging:** verbose registration / token paths use **`devLog`** and only emit when **`import.meta.env.DEV`** is true, so production consoles stay quiet; `console.warn` in some failure paths may still appear for operational diagnostics.

### 2.3 Foreground vs background

- **Background**
  - File: `frontend/public/firebase-messaging-sw.js` — **generated file** (gitignored). Source of truth: [`frontend/docker/firebase-messaging-sw.template.js`](../frontend/docker/firebase-messaging-sw.template.js). In dev/build: Vite plugin `firebaseSwPlugin` (`vite.config.ts`) reads the template and replaces `${VITE_*}` placeholders with values from `loadEnv`; in Docker: `envsubst` in `40-render-config.sh` at container start. Config is baked in at startup — no `postMessage` timing issues.
  - **`messaging.onBackgroundMessage`:** Firebase's managed handler — the primary display path. Calls `showNotification` with `title`/`body`/`vibrate` from `payload.data`. On browsers/platforms where it fires, it handles the push event internally and suppresses the raw `push` listener below.
  - **Raw `push` event listener (fallback):** `self.addEventListener('push', ...)` with `event.waitUntil(registration.showNotification(...))` using `title`/`body` from `event.data.json().data`. Acts as a **fallback** for browsers where `onBackgroundMessage` does **not** fire for data-only FCM messages (notably Chrome when the tab is closed). The two do not double-fire on the same platform — `onBackgroundMessage` suppresses the raw event when it handles the message.

- **Foreground**
  - File: [`frontend/src/services/fcm.ts`](../frontend/src/services/fcm.ts)
  - `onMessage` → `showForegroundNotification`:
    - **Guard:** `chat.message_sent` events are filtered out (`if (payload.data?.event_key === 'chat.message_sent') return`) — chat messages already arrive in real-time via WebSocket, so a duplicate FCM toast is suppressed.
    - [`triggerNotificationToast`](../frontend/src/components/NotificationToast/NotificationToast.tsx) — fixed toast at top of app (mounted in Layout).
    - [`playNotificationChime`](../frontend/src/utils/notificationSound.ts) — optional sound (subject to browser autoplay rules).
  - Title/body are taken from **`payload.data.title` / `payload.data.body`** first, then fall back to `payload.notification` if the SDK surfaces them — see [`frontend/src/services/fcm.ts`](../frontend/src/services/fcm.ts) (`showForegroundNotification`).

### 2.4 In-app toast shell

- Component: [`frontend/src/components/NotificationToast/NotificationToast.tsx`](../frontend/src/components/NotificationToast/NotificationToast.tsx) + CSS module; **mounted once in** [`App.tsx`](../frontend/src/App.tsx) (not inside `Layout` / `AdminLayout`).
- Exported `triggerNotificationToast({ title, body })` from [`notificationToast.utils.ts`](../frontend/src/components/NotificationToast/notificationToast.utils.ts) sets global toast state; auto-dismiss ~5s and manual close.

### 2.5 Firebase config (Vite env)

- File: [`frontend/src/config/firebase.ts`](../frontend/src/config/firebase.ts)
- Env vars (see [`frontend/.env.example`](../frontend/.env.example)):
  - `VITE_FIREBASE_*` (apiKey, authDomain, projectId, storageBucket, messagingSenderId, appId, measurementId)
  - `VITE_FIREBASE_VAPID_KEY` — required for `getToken` on web.
- **Service worker config:** single source of truth is [`frontend/docker/firebase-messaging-sw.template.js`](../frontend/docker/firebase-messaging-sw.template.js). The generated `public/firebase-messaging-sw.js` is gitignored. **Dev:** Vite plugin `firebaseSwPlugin` in [`vite.config.ts`](../frontend/vite.config.ts) runs on `buildStart`, reads the template, replaces `${VITE_*}` placeholders via `loadEnv`, and writes the output. **Prod (Docker):** `envsubst` in [`40-render-config.sh`](../frontend/docker/40-render-config.sh) does the same at container start.

### 2.6 Dev test UI

- [`frontend/src/pages/FCMCheck.tsx`](../frontend/src/pages/FCMCheck.tsx) — permission, token, server registration, foreground logging.

## 3) Backend Flow (Token + Push)

### 3.1 Token API

- Route: [`backend/app/domain/users/router.py`](../backend/app/domain/users/router.py) — `PATCH /users/fcm-token` (mounted under `/api/v1/users` via [`api_router.py`](../backend/app/api/v1/api_router.py)).
- Body: `FCMTokenUpdate` — `fcm_token` may be a string or **`null`** to clear the stored token (logout / device change).
- Persistence: `update_fcm_token` in users service/CRUD; column `users.fcm_token` (nullable).

### 3.2 Outbox → worker → push

- Mappings: [`backend/app/domain/notifications/config/mappings.py`](../backend/app/domain/notifications/config/mappings.py)
- Worker entrypoint: [`backend/app/workers/notification_worker.py`](../backend/app/workers/notification_worker.py) (+ [`backend/app/workers/tasks/notification_tasks.py`](../backend/app/workers/tasks/notification_tasks.py))
- Orchestration: [`backend/app/domain/notifications/core/handler.py`](../backend/app/domain/notifications/core/handler.py) (`NotificationHandler.handle_event` — אורקסטרציה קצרה + שלבי pipeline פרטיים `_resolve_*` / `_dispatch`), [`manager.py`](../backend/app/domain/notifications/manager.py)
- **Session into providers:** [`NotificationCommand`](../backend/app/domain/notifications/manager.py) includes optional **`db`**; the handler sets it from the active **`AsyncSession`**. All providers implement **`send(..., db=None)`**; only push uses **`db`** for persistence side effects (see §3.4).

### 3.3 FCM client (server: `data` map only)

- File: [`backend/app/domain/notifications/channels/push/client.py`](../backend/app/domain/notifications/channels/push/client.py)
- Sends via **`asyncio.get_running_loop().run_in_executor`** (non-blocking Firebase SDK call). **Retries (Tenacity):** only transient Firebase Admin errors (**`UnavailableError`**, **`InternalError`**, **`DeadlineExceededError`**, **`UnknownError`**); **`UnregisteredError`** / **`SenderIdMismatchError`** are **not** retried (invalid registration).
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

### 3.4 Push provider — invalid token cleanup

- File: [`backend/app/domain/notifications/providers/push_provider.py`](../backend/app/domain/notifications/providers/push_provider.py)
- On **`UnregisteredError`** or **`SenderIdMismatchError`**, if **`db`** is present, calls **`crud_user.update_fcm_token(db, user=user, token=None)`** (commits via CRUD), then **returns cleanly** — an expired/unregistered token is an expected lifecycle event, not an error. Logging at `info` level (not `warning`); no re-raise, so `NotificationManager._safe_send` does not log a false failure or trigger retry logic.

### 3.5 Firebase Admin init

- [`backend/app/infrastructure/firebase_core/firebase.py`](../backend/app/infrastructure/firebase_core/firebase.py) — production source of truth is `FIREBASE_CREDENTIALS_JSON` (Model B). `FIREBASE_SERVICE_ACCOUNT_PATH` is local-dev fallback only.
- Workers load the same module and therefore must receive the same env contract.

### 3.6 Docker Compose — production secret contract

- Firebase credentials are not baked into the image and are not mounted as credential files in production.
- Runtime source is `backend/.env` via `env_file` for backend/worker services, with:

  `FIREBASE_CREDENTIALS_JSON={...single-line-json...}`

- Post-deploy assertion should verify the env reached runtime:

  `docker exec linkup_backend printenv | grep FIREBASE_CREDENTIALS_JSON`

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
3. **Skip push:** missing `fcm_token` — provider skips. **Invalid registration** from FCM (`UnregisteredError` / `SenderIdMismatchError`) — **`PushProvider`** clears **`users.fcm_token`** in DB when **`db`** is passed and **returns cleanly** (no re-raise; see §3.4).
4. **Duplicate notifications:** `onBackgroundMessage` is the primary handler; the raw `push` listener is a fallback for browsers that do not fire `onBackgroundMessage` for data-only payloads. Firebase suppresses the raw `push` event when `onBackgroundMessage` handles the message, so the two do not double-fire on the same platform.
5. **Permissions:** site notifications must be **Allow** for token + SW display.

## 6) File Inventory (FCM-related)

| Area | Files |
|------|--------|
| Frontend FCM | `frontend/src/services/fcm.ts` (`initFCM`, **`cleanupFCM`**), `frontend/src/config/firebase.ts`, `frontend/public/firebase-messaging-sw.js` (**generated file**, gitignored; source of truth: `frontend/docker/firebase-messaging-sw.template.js`; dev/build: Vite plugin `firebaseSwPlugin` in `vite.config.ts`; prod: `envsubst` in `40-render-config.sh`; **`importScripts`** Firebase compat SDK version aligned with **`firebase` npm** in `frontend/package.json`, e.g. **11.10.0**) |
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

## 8) Scheduled reminders (ReminderScheduler → handler)

Reminder events (`PICKUP_REMINDER_PASSENGER`, `RIDE_START_DRIVER`) are dispatched on both **email** and **push** channels.

`ReminderScheduler` calls `NotificationHandler.handle_event` with an in-process payload (not the outbox). **Contract:** `scheduled_notification_id`, `ride_id`, and `user_id` together identify a due row in `scheduled_notifications` and tell the handler to hydrate a **`ScheduledReminderSource`**: the **ride** (with driver) supplies template context (`RideBuilder`); **`user_id`** is the recipient. Without all three fields, `ride_id` alone still loads a bare `Ride` and the usual resolver/builder paths apply. See [`backend/app/domain/notifications/core/scheduled_reminder_source.py`](../backend/app/domain/notifications/core/scheduled_reminder_source.py).

## 9) Chat message push (offline fallback)

When a chat message is sent, the outbox event `chat.message_sent` targets **both** `REDIS` (real-time WebSocket delivery via chat-ws) and `RABBITMQ` (offline push fallback). The notification worker's custom handler `handle_chat_message_push` in [`notification_tasks.py`](../backend/app/workers/tasks/notification_tasks.py):

1. **Presence check:** queries Redis DB 1 for `EXISTS presence:{recipient_id}` (set by chat-ws Go service on WebSocket connect, 60s TTL refreshed on each ping). If online → skip.
2. **Debounce:** `SET NX` on `chat_push_debounce:{recipient_id}:{conversation_id}` with 30s TTL. If key exists → skip (max 1 push per conversation per 30 seconds).
3. **Dispatch:** loads sender + recipient from DB, builds `NotificationCommand` with template `chat_message` and channel `["push"]`, dispatches via `NotificationManager`.

**SW notification collapsing:** the FCM data payload includes `conversation_id`; the service worker uses `tag: 'chat-' + conversation_id` with `renotify: true` — the browser replaces (not stacks) notifications for the same conversation.

## 10) Related docs

- [`docs/ENGINEERING_HIGHLIGHTS.md`](ENGINEERING_HIGHLIGHTS.md) — portfolio summary (includes FCM).
- [`docs/architecture/API.md`](architecture/API.md) — `PATCH /fcm-token`.
- [`docs/architecture/EVENTS.md`](architecture/EVENTS.md) — notifications queue.
