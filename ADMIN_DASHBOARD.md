# Admin Dashboard

Admin UI is a **feature module** under `frontend/src/features/admin/` — dark sidebar shell, CSS Modules, RTL-friendly (`dir="rtl"` on shell). **Desktop-oriented:** persistent sidebar (no mobile drawer / off-canvas menu); operators are expected to use a normal browser width; end-user mobile traffic uses the separate **`mobile/`** app.

## Architecture

- **Entry point**: `http://localhost:5173/admin`
- **Auth**: `AuthContext` + `AdminRoute` — משתמש מחובר + **`user.is_admin`** (השדה מגיע מתשובות login / Google sign-in / refresh ב־`LoginUserInfo`; אין לולאת `useEffect` / `refreshUser` ייעודית לדף האדמין).
- **Bundle**: Lazy-loaded via `React.lazy` per route.
- **Toasts**: `NotificationToast` + `triggerNotificationToast` inside admin layout.
- **Mutations**: `ConfirmModal` before destructive or sensitive actions; loading on confirm button; lists refresh after success.
- **Backend**: `/api/v1/admin/*` with `get_current_admin_user`; admin actions logged via `[admin_audit]` logger.

## File structure (excerpt)

```
frontend/src/features/admin/
  api/
    admin.ts, stats.ts, health.ts, users.ts, rides.ts, groups.ts, outbox.ts, lookup.ts
  components/
    AdminRoute.tsx
  pages/
    AdminLayout.tsx, AdminHome.tsx, AdminHealth.tsx, AdminUsers.tsx,
    AdminRides.tsx, AdminGroups.tsx, AdminOutbox.tsx, AdminLookup.tsx
  styles/
    AdminShell.module.css, AdminPage.module.css
  index.ts
```

## Screens & API

כל הנתיבים עם קידומת **`/api/v1/admin`** (הטבלה מקוצרת ל-`/admin/...`).

| Screen   | Endpoints |
|----------|-----------|
| (API)    | `GET /admin/me` — אימות מצב אדמין בשרת (מיוצא ב-`frontend/src/features/admin/api/admin.ts` כ-`fetchAdminMe`; ה-UI נשען בעיקר על `AuthContext` + `AdminRoute`) |
| Home     | `GET /admin/stats` (אגרגציות + `users_per_day`) |
| Health   | `GET /admin/health` (אותו `check_health` כמו בריאות ציבורית, מאחורי אדמין) |
| Users    | `GET /admin/users` (query: `limit`, עד 200), `PATCH /admin/users/{id}/active`, `PATCH /admin/users/{id}/admin` |
| Rides    | `GET /admin/rides` (query: `status` = `active` \| `completed` \| `cancelled` או חסר לכל האחרונות; `limit` עד 500), `POST /admin/rides/{ride_id}/cancel` |
| Groups   | `GET /admin/groups` (query: `limit` עד 500) |
| Outbox   | `GET /admin/outbox`, `GET /admin/outbox/{event_id}`, `POST /admin/outbox/{event_id}/requeue` (רק **FAILED**) |
| Lookup   | `GET /admin/rides/{ride_id}`, `GET /admin/bookings/{booking_id}` |

**403 לא-אדמין:** `get_current_admin_user` מעלה **`AdminAccessRequiredError`** — **403** עם פורמט JSON אחיד (`error_code`: **`ADMIN_ACCESS_REQUIRED`**) — ראו [`docs/ERRORS.md`](docs/ERRORS.md).

## Step 5 — optional later

Deeper audit trail (DB), more group/ride mutations, pagination on large tables.
