import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminAuditLog } from '../api/audit';

export function useAdminAudit(params?: {
  actor_user_id?: string;
  resource_type?: string;
  action?: string;
  created_from?: string;
  created_to?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: qk.admin.audit(params),
    queryFn: async () => {
      const { data } = await fetchAdminAuditLog(params);
      return data;
    },
  });
}
