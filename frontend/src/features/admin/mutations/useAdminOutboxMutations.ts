import { useMutation, useQueryClient } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { postAdminOutboxRequeue } from '../api/outbox';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';

export function useRequeueOutbox() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) => postAdminOutboxRequeue(eventId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.admin.outbox() });
      triggerNotificationToast({ title: 'בוצע', body: 'האירוע הוחזר לתור.' });
    },
    onError: () => {
      triggerNotificationToast({ title: 'שגיאה', body: 'לא ניתן להחזיר לתור.' });
    },
  });
}
