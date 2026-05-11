import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { qk } from '../../../api/queryKeys';
import { postAdminCancelRide } from '../api/rides';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';

export function useCancelAdminRide() {
  const { t } = useTranslation('admin');
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rideId: string) => postAdminCancelRide(rideId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.admin.rides() });
      triggerNotificationToast({ title: t('mutation_done'), body: t('mutation_ride_cancelled') });
    },
    onError: () => {
      triggerNotificationToast({ title: t('mutation_error'), body: t('mutation_ride_cancel_failed') });
    },
  });
}
