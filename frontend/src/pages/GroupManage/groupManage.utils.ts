import type { Ride } from '../../types/api';

export function getRideStatusLabel(r: Ride): string {
  if (r.status === 'cancelled') return 'בוטלה';
  const seats = r.available_seats ?? 0;
  if (seats <= 0) return 'מלא';
  if (seats === 1) return '1 מקום';
  return `${seats} מקומות`;
}

export function isToday(d: Date): boolean {
  const today = new Date();
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  );
}

export function isTomorrow(d: Date): boolean {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return (
    d.getFullYear() === tomorrow.getFullYear() &&
    d.getMonth() === tomorrow.getMonth() &&
    d.getDate() === tomorrow.getDate()
  );
}

export function isThisWeek(d: Date): boolean {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  const t = d.getTime();
  return t >= start.getTime() && t < end.getTime();
}
