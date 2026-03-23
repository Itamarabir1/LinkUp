import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch } from 'react';
import { fetchMyNotifications } from '../api/users';
import type { NotificationItem } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
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
  const [notificationsLoading, setNotificationsLoading] = useState(true);
  const [notificationsError, setNotificationsError] = useState('');
  const isInitialLoadRef = useRef(true);

  const refreshUnreadNotifications = useCallback(async () => {
    const showLoading = isInitialLoadRef.current;
    if (showLoading) {
      setNotificationsLoading(true);
    }
    setNotificationsError('');
    try {
      const { data } = await fetchMyNotifications();
      const list = Array.isArray(data) ? data : [];
      dispatch({ type: 'SET_NOTIFICATION_STATE', list });
    } catch (err) {
      const msg = getApiErrorMessage(err, 'לא ניתן לטעון את ההתראות');
      setNotificationsError(msg);
      if (import.meta.env.DEV) {
        console.warn('[ChatContext] refreshUnreadNotifications:', msg);
      }
      dispatch({ type: 'SET_NOTIFICATION_STATE', list: [] });
    } finally {
      if (showLoading) {
        setNotificationsLoading(false);
      }
      isInitialLoadRef.current = false;
    }
  }, [dispatch]);

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
      isInitialLoadRef.current = true;
      queueMicrotask(() => dispatch({ type: 'RESET_SESSION' }));
      return;
    }
    queueMicrotask(() => void refreshUnreadNotifications());
    const interval = setInterval(() => void refreshUnreadNotifications(), 30000);
    return () => clearInterval(interval);
  }, [userId, refreshUnreadNotifications, dispatch]);

  return {
    refreshUnreadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    isNotificationRead,
    notificationsLoading,
    notificationsError,
  };
}
