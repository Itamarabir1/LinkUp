import { api } from '../../../api/client';

export type AdminGroupRow = {
  group_id: string;
  name: string;
  member_count: number;
  admin_id: string;
  admin_name: string;
  admin_email: string | null;
  is_active: boolean;
  created_at: string | null;
};

export function fetchAdminGroups(params?: { limit?: number }) {
  return api.get<AdminGroupRow[]>('/admin/groups', { params });
}
