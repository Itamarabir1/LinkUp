import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminGroups } from '../api/groups';

export function useAdminGroups(params?: { limit?: number }) {
  return useQuery({
    queryKey: qk.admin.groups(params),
    queryFn: async () => {
      const { data } = await fetchAdminGroups(params);
      return Array.isArray(data) ? data : [];
    },
    staleTime: 30_000,
  });
}
