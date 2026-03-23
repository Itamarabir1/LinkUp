import { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getNotificationItemKey, useChat } from '../context/ChatContext';
import type { NotificationItem } from '../types/api';
import { NOTIFICATION_GROUP_ORDER, getTimeGroup } from './notifications.utils';

export function useNotifications() {
  const navigate = useNavigate();
  const {
    notificationList: list,
    notificationsLoading: loading,
    notificationsError: error,
    markNotificationRead,
    markAllNotificationsRead,
    isNotificationRead,
    unreadNotifications,
  } = useChat();

  // סימון כל פריט כנקרא ברגע שהרשימה נטענת
  useEffect(() => {
    if (list.length === 0) return;
    for (const n of list) {
      const key = getNotificationItemKey(n);
      if (!isNotificationRead(key)) {
        markNotificationRead(key);
      }
    }
  }, [list, isNotificationRead, markNotificationRead]);

  const grouped = useCallback(() => {
    const groups: Record<string, NotificationItem[]> = {};
    NOTIFICATION_GROUP_ORDER.forEach((g) => {
      groups[g] = [];
    });
    list.forEach((n) => {
      const g = getTimeGroup(n.created_at);
      if (!groups[g]) groups[g] = [];
      groups[g].push(n);
    });
    return NOTIFICATION_GROUP_ORDER.filter((g) => groups[g].length > 0).map((g) => ({
      label: g,
      items: groups[g],
    }));
  }, [list]);

  const handleRowClick = (n: NotificationItem) => {
    const key = getNotificationItemKey(n);
    if (!isNotificationRead(key)) markNotificationRead(key);
    if (n.action_url) navigate(n.action_url);
  };

  return {
    loading,
    error,
    list,
    grouped,
    handleRowClick,
    unreadNotifications,
    markAllNotificationsRead,
    isNotificationRead,
  };
}
