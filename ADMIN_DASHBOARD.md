# Admin Dashboard

Admin UI is built as a **feature module** inside the main frontend app, under `frontend/src/features/admin/`.

## Architecture

- **Entry point**: `http://localhost:5173/admin`
- **Auth**: Uses the existing `AuthContext` — no separate login needed. `AdminRoute` checks `user.is_admin` before rendering anything.
- **is_admin hydration**: After login, the user object may arrive without `is_admin`.
  `AdminRoute` detects this (`is_admin === undefined`) and calls `refreshUser()`
  (which fetches `GET /users/me`) before deciding to allow or redirect.
- **Bundle**: Lazy-loaded via `React.lazy` — admin code is never sent to non-admin users.
- **Backend**: Admin-only endpoints under `/api/v1/admin/*`, protected by `get_current_admin_user` dependency.

## File structure

```
frontend/src/features/admin/
  api/
    admin.ts       — GET /admin/me
    health.ts      — GET /admin/health
    users.ts       — GET /admin/users
    outbox.ts      — GET /admin/outbox, GET /admin/outbox/{id}
    lookup.ts      — GET /admin/rides/{id}, GET /admin/bookings/{id}
  components/
    AdminRoute.tsx — Protected route: redirects if not admin
  pages/
    AdminLayout.tsx — Shell with nav + logout
    AdminHome.tsx
    AdminHealth.tsx
    AdminUsers.tsx
    AdminOutbox.tsx
    AdminLookup.tsx
  index.ts         — Barrel export
```

## Screens

| Screen  | Backend endpoint                                      | Status      |
|---------|-------------------------------------------------------|-------------|
| Home    | —                                                     | ✅ Done     |
| Health  | `GET /api/v1/admin/health`                            | ✅ Done     |
| Users   | `GET /api/v1/admin/users`                             | ✅ Done     |
| Outbox  | `GET /api/v1/admin/outbox`, `/outbox/{id}`            | ✅ Done     |
| Lookup  | `GET /api/v1/admin/rides/{id}`, `/bookings/{id}`      | ✅ Done     |

## Step 5 — Controlled mutations (optional, later)

Only after read-only is stable: deactivate user, cancel ride, requeue outbox event.
Add audit trail concepts before enabling.
