import { useCallback, useEffect } from 'react';
import type { Dispatch } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchMyNotifications } from '../api/users';
import { qk } from '../api/queryKeys';
import type { NotificationItem } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import {
  getNotificationItemKey,
  getReadNotificationSet,
  saveReadNotificationSet,
} from './chatNotificationStorage';
import type { ChatAction } from './chatState';

export function useChatNotificationsFeed(
  userId: string | undefined,
  notificationList: NotificationItem[],
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
      return Array.isArray(data.items) ? data.items : [];
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
    (key: string) => {
      const set = getReadNotificationSet();
      set.add(key);
      saveReadNotificationSet(set);
      dispatch({ type: 'DECREMENT_UNREAD_NOTIFICATIONS' });
    },
    [dispatch]
  );

  const markAllNotificationsRead = useCallback(() => {
    const set = getReadNotificationSet();
    notificationList.forEach((n) => set.add(getNotificationItemKey(n)));
    saveReadNotificationSet(set);
    dispatch({ type: 'MARK_ALL_NOTIFICATIONS_READ' });
  }, [notificationList, dispatch]);

  const isNotificationRead = useCallback(
    (key: string) => getReadNotificationSet().has(key),
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
      dispatch({ type: 'SET_NOTIFICATION_STATE', list: [] });
    }
  }, [isError, dispatch, notificationsError]);

  useEffect(() => {
    if (!userId || data === undefined) return;
    dispatch({ type: 'SET_NOTIFICATION_STATE', list: data });
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
