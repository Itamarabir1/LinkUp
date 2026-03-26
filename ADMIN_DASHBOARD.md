# Admin Dashboard

Admin UI is a **feature module** under `frontend/src/features/admin/` — dark sidebar shell, CSS Modules, RTL-friendly (`dir="rtl"` on shell).

## Architecture

- **Entry point**: `http://localhost:5173/admin`
- **Auth**: `AuthContext` + `AdminRoute` (`user.is_admin`, with `refreshUser()` hydration when `is_admin` is missing after login).
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

| Screen   | Endpoints |
|----------|-----------|
| Home     | `GET /admin/stats` (aggregates) |
| Health   | `GET /admin/health` |
| Users    | `GET /admin/users`, `PATCH .../users/{id}/active`, `PATCH .../users/{id}/admin` |
| Rides    | `GET /admin/rides?status=`, `POST /admin/rides/{id}/cancel` |
| Groups   | `GET /admin/groups` |
| Outbox   | `GET /admin/outbox`, `GET .../outbox/{id}`, `POST .../outbox/{id}/requeue` (FAILED only) |
| Lookup   | `GET /admin/rides/{id}`, `GET /admin/bookings/{id}` |

## Step 5 — optional later

Deeper audit trail (DB), more group/ride mutations, pagination on large tables.
