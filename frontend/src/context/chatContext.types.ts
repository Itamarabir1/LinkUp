import type { ReactNode } from 'react';
import type { NotificationItem } from '../types/api';

export interface ChatContextValue {
  openConversationId: string | null;
  panelConversationId: string | null;
  openChat: (conversationId: string) => void;
  closeChat: () => void;
  unreadMessages: number;
  refreshUnread: () => void;
  unreadNotifications: number;
  notificationList: NotificationItem[];
  notificationsLoading: boolean;
  notificationsError: string;
  markNotificationRead: (n: NotificationItem) => void;
  markAllNotificationsRead: () => void;
  refreshUnreadNotifications: () => void;
  isNotificationRead: (n: NotificationItem) => boolean;
}

export interface ChatProviderProps {
  children: ReactNode;
}
