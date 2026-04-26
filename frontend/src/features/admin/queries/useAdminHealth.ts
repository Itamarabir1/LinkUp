import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminHealth } from '../api/health';

export function useAdminHealth() {
  return useQuery({
    queryKey: qk.admin.health(),
    queryFn: async () => {
      const { data } = await fetchAdminHealth();
      return data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
