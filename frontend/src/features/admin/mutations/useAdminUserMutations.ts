import { useMutation, useQueryClient } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { patchAdminUserActive, patchAdminUserAdmin } from '../api/users';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';

export function useToggleUserActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => patchAdminUserActive(userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.admin.users() });
      triggerNotificationToast({ title: 'עודכן', body: 'סטטוס פעילות המשתמש עודכן.' });
    },
    onError: () => {
      triggerNotificationToast({ title: 'שגיאה', body: 'הפעולה נכשלה.' });
    },
  });
}

export function useToggleUserAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, makeAdmin }: { userId: string; makeAdmin: boolean }) =>
      patchAdminUserAdmin(userId, makeAdmin ? 'grant' : 'revoke'),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: qk.admin.users() });
      triggerNotificationToast({ title: 'עודכן', body: 'סטטוס אדמין עודכן.' });
    },
    onError: () => {
      triggerNotificationToast({ title: 'שגיאה', body: 'הפעולה נכשלה.' });
    },
  });
}
