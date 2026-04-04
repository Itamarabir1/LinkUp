/**
 * מפתחות localStorage — מקור אמת יחיד.
 * שינוי שם כאן משפיע על כל הפרויקט.
 */
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'linkup_access_token',
  REFRESH_TOKEN: 'linkup_refresh_token',
} as const;

/** הודעות שגיאה משותפות ל-UI */
export const ERROR_MESSAGES = {
  BACKEND_TIMEOUT:
    'השרת לא מגיב בזמן. וודא שהבקאנד רץ (למשל http://localhost:8000) ושה-Vite proxy מפנה ל-/api/v1.',
} as const;
