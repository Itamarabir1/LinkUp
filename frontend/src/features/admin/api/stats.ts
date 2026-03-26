import { api } from '../../../api/client';

export type AdminStatsResponse = {
  users_total: number;
  rides_active: number;
  bookings_total: number;
  outbox_pending: number;
};

export function fetchAdminStats() {
  return api.get<AdminStatsResponse>('/admin/stats');
}
