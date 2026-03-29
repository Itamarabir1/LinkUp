import { api } from '../../../api/client';

export type AdminStatsResponse = {
  users_total: number;
  rides_active: number;
  bookings_total: number;
  outbox_pending: number;
  users_new_today: number;
  rides_total: number;
  bookings_pending: number;
  bookings_confirmed: number;
  groups_total: number;
  outbox_failed: number;
  active_users_last_7_days: number;
  rides_by_status: Record<string, number>;
  bookings_by_status: Record<string, number>;
  users_per_day: { date: string; count: number }[];
};

export function fetchAdminStats() {
  return api.get<AdminStatsResponse>('/admin/stats');
}
