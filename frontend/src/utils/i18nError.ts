import i18n from '../i18n';

/**
 * Sync API error fallback from the `common` namespace (`err_*` keys).
 * Use inside hooks and non-React modules where `useTranslation` is unavailable.
 */
export function apiErr(key: string): string {
  return i18n.t(`common:${key}`);
}
