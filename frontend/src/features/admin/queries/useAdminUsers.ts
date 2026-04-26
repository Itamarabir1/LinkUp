import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminUsers } from '../api/users';

export function useAdminUsers(params?: { q?: string; limit?: number }) {
  return useQuery({
    queryKey: qk.admin.users(params),
    queryFn: async () => {
      const { data } = await fetchAdminUsers(params);
      return Array.isArray(data) ? data : [];
    },
    staleTime: 30_000,
  });
}
