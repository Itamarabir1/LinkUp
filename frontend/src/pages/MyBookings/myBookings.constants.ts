import i18n from '../../i18n';

export const AVATAR_COLORS = [
  '#6366f1',
  '#059669',
  '#d97706',
  '#dc2626',
  '#7c3aed',
  '#0ea5e9',
] as const;

export const STATUS_LABEL: Record<string, string> = {
  pending_approval: i18n.t('bookings:bookingStatus_pending'),
  confirmed: i18n.t('bookings:bookingStatus_approved'),
  rejected: i18n.t('bookings:bookingStatus_rejected'),
  cancelled: i18n.t('bookings:bookingStatus_cancelled'),
  completed: i18n.t('rides:status_completed'),
};
