import { useCallback, useEffect } from 'react';
import type { Dispatch } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchMyNotifications, markNotificationsReadApi, markAllNotificationsReadApi } from '../api/users';
import { qk } from '../api/queryKeys';
import type { NotificationItem } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import type { ChatAction } from './chatState';

export function getNotificationItemKey(n: { booking_id: string; created_at: string }): string {
  return `${n.booking_id}_${n.created_at}`;
}

export function useChatNotificationsFeed(
  userId: string | undefined,
  dispatch: Dispatch<ChatAction>
) {
  const queryClient = useQueryClient();

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: qk.notifications.all(),
    queryFn: async () => {
      const { data } = await fetchMyNotifications({ limit: 20 });
      return data;
    },
    enabled: !!userId,
    staleTime: 0,
    refetchInterval: 5 * 60_000,
    refetchOnReconnect: false,
  });
  const notificationsLoading = !!userId && isLoading && data === undefined;
  const notificationsError =
    userId && isError ? getApiErrorMessage(error, apiErr('err_load_notifications')) : '';

  const markNotificationRead = useCallback(
    (n: NotificationItem) => {
      markNotificationsReadApi([{ booking_id: n.booking_id, created_at: n.created_at }]).catch(
        () => {}
      );
      dispatch({ type: 'DECREMENT_UNREAD_NOTIFICATIONS' });
      void queryClient.invalidateQueries({ queryKey: qk.notifications.all() });
    },
    [dispatch, queryClient]
  );

  const markAllNotificationsRead = useCallback(() => {
    markAllNotificationsReadApi().catch(() => {});
    dispatch({ type: 'MARK_ALL_NOTIFICATIONS_READ' });
    void queryClient.invalidateQueries({ queryKey: qk.notifications.all() });
  }, [dispatch, queryClient]);

  const isNotificationRead = useCallback(
    (n: NotificationItem) => !!n.is_read,
    []
  );

  useEffect(() => {
    if (!userId) {
      queueMicrotask(() => dispatch({ type: 'RESET_SESSION' }));
      queryClient.removeQueries({ queryKey: qk.notifications.all() });
      return;
    }
  }, [userId, dispatch, queryClient]);

  useEffect(() => {
    if (isError) {
      if (import.meta.env.DEV) {
        console.warn('[ChatContext] refreshUnreadNotifications:', notificationsError);
      }
      dispatch({ type: 'SET_NOTIFICATION_STATE', list: [], unreadCount: 0 });
    }
  }, [isError, dispatch, notificationsError]);

  useEffect(() => {
    if (!userId || data === undefined) return;
    dispatch({
      type: 'SET_NOTIFICATION_STATE',
      list: Array.isArray(data.items) ? data.items : [],
      unreadCount: data.unread_count ?? 0,
    });
  }, [data, dispatch, userId]);

  const refreshUnreadNotifications = useCallback(() => {
    if (!userId) return;
    void queryClient.invalidateQueries({ queryKey: qk.notifications.all() });
  }, [queryClient, userId]);

  return {
    refreshUnreadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    isNotificationRead,
    notificationsLoading,
    notificationsError,
  };
}
