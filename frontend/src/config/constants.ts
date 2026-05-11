/**
 * localStorage keys — single source of truth.
 * Renaming here affects the whole project.
 */
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'linkup_access_token',
} as const;

/** `window` CustomEvent name: notifications list should refetch (WS reconnect / server push). */
export const NOTIFICATIONS_REFRESH_EVENT = 'linkup-notifications-refresh' as const;
