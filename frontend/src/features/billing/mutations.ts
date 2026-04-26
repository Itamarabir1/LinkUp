import { useMutation } from '@tanstack/react-query';
import { mk } from '../../api/queryKeys';
import { createCheckoutSession } from '../../api/billing';

export function useCreateCheckoutSession() {
  return useMutation({
    mutationKey: mk.billing.checkout(),
    mutationFn: createCheckoutSession,
    onSuccess: ({ checkout_url }) => {
      window.location.assign(checkout_url);
    },
  });
}
