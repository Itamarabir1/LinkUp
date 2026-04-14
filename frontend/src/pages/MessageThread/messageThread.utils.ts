import i18n from '../../i18n';
import { getLocale } from '../../utils/date';

export function formatChatLastSeen(isoString: string | null | undefined): string {
  if (isoString == null || String(isoString).trim() === '') return '';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '';

  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  const locale = getLocale();

  if (diffMins < 1) return i18n.t('common:justNow');
  if (diffMins < 60) return i18n.t('common:minutesAgo', { count: diffMins });

  const time = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round((today.getTime() - dayStart.getTime()) / 86400000);

  if (diffDays === 0) return i18n.t('common:todayAt', { time });
  if (diffDays === 1) return i18n.t('common:yesterdayAt', { time });

  if (diffDays < 7) {
    const dayName = date.toLocaleDateString(locale, { weekday: 'long' });
    return i18n.t('common:dayAt', { day: dayName, time });
  }

  const dateStr = date.toLocaleDateString(locale, { day: '2-digit', month: '2-digit' });
  return i18n.t('common:date_at_time', { date: dateStr, time });
}
