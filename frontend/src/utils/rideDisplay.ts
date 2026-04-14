import type { Ride } from '../types/api';

/** קבוצות למיפוי שם תצוגה (מקור נסיעה / בקשה) */
export type GroupNameRef = { group_id: string; name: string };

/**
 * תווית מקור לנסיעה או בקשה: שם קבוצה או "ציבורי".
 */
export function getRideSourceLabel(
  groupId: string | null | undefined,
  myGroups: GroupNameRef[]
): string {
  if (!groupId) return 'ציבורי';
  const g = myGroups.find((x) => x.group_id === groupId);
  return g?.name ?? 'ציבורי';
}

export function getRideStatusLabel(r: Ride): string {
  if (r.status === 'cancelled') return 'בוטלה';
  if (r.status === 'completed') return 'הושלמה';
  if (r.status === 'active') return 'פעילה';
  const seats = r.available_seats ?? 0;
  if (seats <= 0) return 'מלא';
  if (seats === 1) return '1 מקום';
  return `${seats} מקומות`;
}

const REQUEST_STATUS_LABELS: Record<string, string> = {
  active: 'מחפש',
  pending: 'ממתין לאישור',
  approved: 'אושר',
  rejected: 'נדחה',
  completed: 'הושלם',
  expired: 'פג תוקף',
  matched: 'נמצאה נסיעה',
  cancelled: 'בוטל',
};

export function getRequestStatusLabel(status: string): string {
  return REQUEST_STATUS_LABELS[status] ?? status;
}

