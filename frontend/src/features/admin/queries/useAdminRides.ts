import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminRides } from '../api/rides';

export function useAdminRides(params?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: qk.admin.rides(params),
    queryFn: async () => {
      const { data } = await fetchAdminRides(params);
      return Array.isArray(data) ? data : [];
    },
    staleTime: 30_000,
  });
}
