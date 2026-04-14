export const RIDE_STATUS_COLORS: Record<string, string> = {
  open: '#4f6ef7',
  full: '#f59e0b',
  active: '#22c55e',
  completed: '#818cf8',
  cancelled: '#ef4444',
};

export const RIDE_STATUS_LABELS: Record<string, string> = {
  open: 'פתוח',
  full: 'מלא',
  active: 'פעיל',
  completed: 'הושלם',
  cancelled: 'בוטל',
};

export const BOOKING_STATUS_COLORS: Record<string, string> = {
  pending_approval: '#f59e0b',
  confirmed: '#22c55e',
  rejected: '#ef4444',
  cancelled: '#475569',
  completed: '#818cf8',
  en_route: '#4f6ef7',
  arrived: '#06b6d4',
  trip_in_progress: '#a855f7',
};

export const BOOKING_STATUS_LABELS: Record<string, string> = {
  pending_approval: 'ממתין לאישור',
  confirmed: 'מאושר',
  rejected: 'נדחה',
  cancelled: 'בוטל',
  completed: 'הושלם',
  en_route: 'בדרך',
  arrived: 'הגיע',
  trip_in_progress: 'בנסיעה',
};
