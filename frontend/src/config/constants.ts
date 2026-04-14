/**
 * localStorage keys — single source of truth.
 * Renaming here affects the whole project.
 */
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'linkup_access_token',
  REFRESH_TOKEN: 'linkup_refresh_token',
} as const;

/** Shared user-facing error messages. */
export const ERROR_MESSAGES = {
  BACKEND_TIMEOUT:
    'השרת לא מגיב בזמן. וודא שהבקאנד רץ (למשל http://localhost:8000) ושה-Vite proxy מפנה ל-/api/v1.',
} as const;
