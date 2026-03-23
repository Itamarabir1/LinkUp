const NOTIF_READ_KEY = 'linkup_notif_read';

/** מפתח ייחודי לפריט התראה (ל־localStorage + markNotificationRead). */
export function getNotificationItemKey(n: { booking_id: string; created_at: string }): string {
  return `${n.booking_id}_${n.created_at}`;
}

export function getReadNotificationSet(): Set<string> {
  try {
    const raw = localStorage.getItem(NOTIF_READ_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

export function saveReadNotificationSet(set: Set<string>) {
  try {
    localStorage.setItem(NOTIF_READ_KEY, JSON.stringify([...set]));
  } catch {
    // ignore
  }
}
