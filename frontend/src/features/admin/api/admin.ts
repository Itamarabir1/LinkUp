import { api } from '../../../api/client';

export type AdminMeResponse = {
  user_id: string;
  email: string | null;
  full_name: string;
  is_admin: boolean;
};

export function fetchAdminMe() {
  return api.get<AdminMeResponse>('/admin/me');
}
