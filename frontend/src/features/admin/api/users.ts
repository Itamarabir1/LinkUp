import { api } from '../../../api/client';

export type AdminUserRow = {
  user_id: string;
  full_name: string;
  email: string | null;
  phone_number: string;
  is_active: boolean;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string | null;
  last_login: string | null;
};

export function fetchAdminUsers(params?: {
  q?: string;
  is_active?: boolean;
  is_admin?: boolean;
  is_verified?: boolean;
  limit?: number;
}) {
  return api.get<AdminUserRow[]>('/admin/users', { params });
}

export function patchAdminUserActive(userId: string) {
  return api.patch<{ user_id: string; is_active: boolean }>(
    `/admin/users/${userId}/active`
  );
}

export function patchAdminUserAdmin(userId: string) {
  return api.patch<{ user_id: string; is_admin: boolean }>(
    `/admin/users/${userId}/admin`
  );
}
