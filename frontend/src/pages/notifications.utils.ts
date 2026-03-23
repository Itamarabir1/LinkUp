export type DisplayType =
  | 'booking_approved'
  | 'booking_rejected'
  | 'ride_cancelled'
  | 'booking_request'
  | 'booking_cancelled_by_passenger'
  | 'group_joined'
  | 'group_member_joined'
  | 'pending_approval'
  | 'default';

/** מיפוי type מהבקאנד לסוג תצוגה (אייקון + סגנון). */
export function getDisplayType(type: string): DisplayType {
  if (type === 'booking_confirmed') return 'booking_approved';
  if (type === 'ride_request') return 'booking_request';
  if (type === 'pending_approval') return 'pending_approval';
  const known: DisplayType[] = [
    'booking_approved',
    'booking_rejected',
    'ride_cancelled',
    'booking_request',
    'booking_cancelled_by_passenger',
    'group_joined',
    'group_member_joined',
    'pending_approval',
  ];
  return known.includes(type as DisplayType) ? (type as DisplayType) : 'default';
}

/** קבוצת זמן: היום, אתמול, השבוע, קודם לכן */
export function getTimeGroup(date: string): string {
  const d = new Date(date);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((today.getTime() - dayStart.getTime()) / (24 * 60 * 60 * 1000));
  if (diffDays === 0) return 'היום';
  if (diffDays === 1) return 'אתמול';
  if (diffDays >= 2 && diffDays < 7) return 'השבוע';
  return 'קודם לכן';
}

export const NOTIFICATION_GROUP_ORDER = ['היום', 'אתמול', 'השבוע', 'קודם לכן'] as const;
