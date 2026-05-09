import i18n from '../i18n';

/** Groups for display-name mapping (ride/request source). */
export type GroupNameRef = { group_id: string; name: string };

/**
 */
export function getRideSourceLabel(
  groupId: string | null | undefined,
  myGroups: GroupNameRef[]
): string {
  if (!groupId) return i18n.t('common:public');
  const g = myGroups.find((x) => x.group_id === groupId);
  return g?.name ?? i18n.t('common:public');
}

// Structural subset shared by both the hand-written `Ride` and the generated
// `RideResponse` types — only the fields this label function actually reads.
type RideStatusInfo = {
  status: string;
  available_seats?: number | null;
};

export function getRideStatusLabel(r: RideStatusInfo): string {
  if (r.status === 'cancelled') return i18n.t('rides:status_cancelled');
  if (r.status === 'completed') return i18n.t('rides:status_completed');
  if (r.status === 'active') return i18n.t('rides:status_active');
  const seats = r.available_seats ?? 0;
  if (seats <= 0) return i18n.t('rides:status_full');
  return i18n.t('common:seats', { count: seats });
}

const REQUEST_STATUS_LABELS: Record<string, string> = {
  active: 'rides:status_open',
  pending: 'rides:pendingApproval',
  approved: 'bookings:bookingStatus_approved',
  rejected: 'bookings:bookingStatus_rejected',
  completed: 'rides:status_completed',
  expired: 'rides:expired',
  matched: 'rides:matchFound',
  cancelled: 'bookings:bookingStatus_cancelled',
};

export function getRequestStatusLabel(status: string): string {
  const key = REQUEST_STATUS_LABELS[status];
  return key ? i18n.t(key) : status;
}

