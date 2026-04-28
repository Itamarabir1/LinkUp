import { api } from '../../../api/client';
import type { AdminPaginated } from './bookings';

export type AdminAuditRow = {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string | null;
};

export function fetchAdminAuditLog(params?: {
  actor_user_id?: string;
  resource_type?: string;
  action?: string;
  created_from?: string;
  created_to?: string;
  limit?: number;
  offset?: number;
}) {
  return api.get<AdminPaginated<AdminAuditRow>>('/admin/audit-log', { params });
}
