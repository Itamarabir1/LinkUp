import { useMutation, useQueryClient } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { postAdminCancelRide } from '../api/rides';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';

export function useCancelAdminRide() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rideId: string) => postAdminCancelRide(rideId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.admin.rides() });
      triggerNotificationToast({ title: 'בוצע', body: 'הנסיעה בוטלה.' });
    },
    onError: () => {
      triggerNotificationToast({ title: 'שגיאה', body: 'לא ניתן לבטל את הנסיעה.' });
    },
  });
}
