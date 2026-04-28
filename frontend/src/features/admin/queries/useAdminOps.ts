import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminQueues, fetchAdminSystemOverview, fetchAdminWorkers } from '../api/ops';

export function useAdminSystemOverview() {
  return useQuery({
    queryKey: qk.admin.opsOverview(),
    queryFn: async () => {
      const { data } = await fetchAdminSystemOverview();
      return data;
    },
    refetchInterval: 15000,
  });
}

export function useAdminQueues() {
  return useQuery({
    queryKey: qk.admin.queues(),
    queryFn: async () => {
      const { data } = await fetchAdminQueues();
      return data;
    },
    refetchInterval: 15000,
  });
}

export function useAdminWorkers() {
  return useQuery({
    queryKey: qk.admin.workers(),
    queryFn: async () => {
      const { data } = await fetchAdminWorkers();
      return data;
    },
    refetchInterval: 15000,
  });
}
