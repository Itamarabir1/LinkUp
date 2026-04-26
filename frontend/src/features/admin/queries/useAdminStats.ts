import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminStats } from '../api/stats';

export function useAdminStats() {
  return useQuery({
    queryKey: qk.admin.stats(),
    queryFn: async () => {
      const { data } = await fetchAdminStats();
      return data;
    },
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
}
