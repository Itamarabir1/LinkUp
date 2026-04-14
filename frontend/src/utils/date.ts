import i18n from '../i18n';

export function getLocale(): 'he-IL' | 'en-US' {
  return i18n.language === 'en' ? 'en-US' : 'he-IL';
}

/** Time only, locale-aware (no seconds). */
export function formatTimeHm(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString(getLocale(), { hour: '2-digit', minute: '2-digit' });
}

/** e.g. "14 April" / "14 באפריל" */
export function formatDayMonthLong(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString(getLocale(), { day: 'numeric', month: 'long' });
}

/** e.g. "April 2026" / "אפריל 2026" */
export function formatMonthYearLong(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString(getLocale(), { month: 'long', year: 'numeric' });
}

export function formatWeekdayLong(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString(getLocale(), { weekday: 'long' });
}

/** Full calendar date (day + month + year), locale-aware. */
export function formatDateFull(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString(getLocale(), {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

/**
 * Locale-aware date+time without seconds.
 */
export function formatDateTimeNoSeconds(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  const locale = getLocale();
  return d.toLocaleString(locale, {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

/** For conversation snippets: minutes ago / HH:mm / yesterday / DD/MM. */
export function formatConversationTime(date: string | Date | null): string {
  if (!date) return '';
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / (60 * 1000));
  if (diffMins < 60) {
    return i18n.t('common:minutesAgo', { count: diffMins });
  }
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const dayDiff = Math.round((today.getTime() - day.getTime()) / (24 * 60 * 60 * 1000));
  if (dayDiff === 0) return formatTimeHm(d);
  if (dayDiff === 1) return i18n.t('common:yesterday');
  return d.toLocaleDateString(getLocale(), { day: '2-digit', month: '2-digit' });
}

/** Short ride format: "Today 08:00", "Tomorrow 07:30", "Friday 05:30". */
export function formatRideDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(d.getTime())) return '';
  const locale = getLocale();
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const rideDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((rideDay.getTime() - today.getTime()) / (24 * 60 * 60 * 1000));
  const time = formatTimeHm(d);
  if (diffDays === 0) return `${i18n.t('common:today')} ${time}`;
  if (diffDays === 1) return `${i18n.t('common:tomorrow')} ${time}`;
  if (diffDays > 1 && diffDays < 7) {
    return `${d.toLocaleDateString(locale, { weekday: 'long' })} ${time}`;
  }
  return formatDateTimeNoSeconds(d);
}

/**
 * Formats a notification timestamp relative to now.
 * - Same day: "לפני X דקות" / "לפני X שעות"
 * - Yesterday: "14:30"
 * - This week: "ב' 14:30" (day abbreviation + time)
 * - Older: "05/04"
 */
export function formatRelativeNotificationTime(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '';
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart.getTime() - 86400000);
  const weekStart = new Date(todayStart.getTime() - 6 * 86400000);

  const locale = getLocale();

  if (d >= todayStart) {
    if (diffMins < 1) return i18n.t('common:time_now');
    if (diffMins < 60) return i18n.t('common:minutesAgo', { count: diffMins });
    return i18n.t('common:hoursAgo', { count: diffHours });
  }

  if (d >= yesterdayStart) {
    return d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  }

  if (d >= weekStart) {
    const day = d.toLocaleDateString(locale, { weekday: 'short' });
    const time = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
    return `${day} ${time}`;
  }

  return d.toLocaleDateString(locale, { day: '2-digit', month: '2-digit' });
}
