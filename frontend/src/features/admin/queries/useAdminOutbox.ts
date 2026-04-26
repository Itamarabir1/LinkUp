import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminOutbox, fetchAdminOutboxById } from '../api/outbox';

export function useAdminOutbox(params?: { status?: string; limit?: number }) {
  return useQuery({
    queryKey: qk.admin.outbox(params),
    queryFn: async () => {
      const { data } = await fetchAdminOutbox(params);
      return Array.isArray(data) ? data : [];
    },
    staleTime: 15_000,
  });
}

export function useAdminOutboxDetail(id: string | null) {
  return useQuery({
    queryKey: ['admin', 'outbox', 'detail', id] as const,
    queryFn: async () => {
      const { data } = await fetchAdminOutboxById(id!);
      return data;
    },
    enabled: !!id,
    staleTime: 0,
  });
}
