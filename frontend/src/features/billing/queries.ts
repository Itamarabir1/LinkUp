import { useQuery } from '@tanstack/react-query';
import type { UseQueryOptions } from '@tanstack/react-query';
import { qk } from '../../api/queryKeys';
import { getBillingStatus, type BillingStatus } from '../../api/billing';

type BillingStatusOptions = Omit<
  UseQueryOptions<BillingStatus, Error, BillingStatus, ReturnType<typeof qk.billing.status>>,
  'queryKey' | 'queryFn' | 'staleTime'
>;

export function useBillingStatus(options?: BillingStatusOptions) {
  return useQuery({
    queryKey: qk.billing.status(),
    queryFn: getBillingStatus,
    staleTime: 5 * 60_000,
    ...options,
  });
}
