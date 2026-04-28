import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminBillingPayments } from '../api/billing';

export function useAdminBilling(params?: {
  status?: string;
  user_id?: string;
  currency?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: qk.admin.billing(params),
    queryFn: async () => {
      const { data } = await fetchAdminBillingPayments(params);
      return data;
    },
  });
}
