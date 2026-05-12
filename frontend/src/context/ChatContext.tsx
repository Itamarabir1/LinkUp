import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { NOTIFICATIONS_REFRESH_EVENT } from '../config/constants';
import { markNotificationsReadApi } from '../api/users';
import { useUserEventStream } from '../hooks/useUserEventStream';
import type { InvalidateEvent, UserEvent } from '../types/wsEvents';
import { useAuth } from './AuthContext';
import type { ChatContextValue, ChatProviderProps } from './chatContext.types';
import { chatReducer, initialChatState } from './chatState';
import { useChatNotificationsFeed } from './useChatNotificationsFeed';
import { useChatOpenClose } from './useChatOpenClose';
import { useChatUnreadMessages } from './useChatUnreadMessages';

export { getNotificationItemKey } from './useChatNotificationsFeed';

const LEGACY_NOTIF_READ_KEY = 'linkup_notif_read';

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within ChatProvider');
  return ctx;
}

export function ChatProvider({ children }: ChatProviderProps) {
  const location = useLocation();
  const { user } = useAuth();
  const [state, dispatch] = useReducer(chatReducer, initialChatState);

  const { openChat, closeChat } = useChatOpenClose(location.pathname, dispatch);
  const { refreshUnread, setUnreadDirect } = useChatUnreadMessages(user?.user_id, dispatch);

  const {
    refreshUnreadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    isNotificationRead,
    notificationsLoading,
    notificationsError,
  } = useChatNotificationsFeed(user?.user_id, dispatch);

  const migrated = useRef(false);
  useEffect(() => {
    if (!user?.user_id || migrated.current) return;
    const raw = localStorage.getItem(LEGACY_NOTIF_READ_KEY);
    if (!raw) return;
    migrated.current = true;
    try {
      const arr = JSON.parse(raw) as string[];
      if (!Array.isArray(arr) || arr.length === 0) {
        localStorage.removeItem(LEGACY_NOTIF_READ_KEY);
        return;
      }
      const items = arr
        .map((key) => {
          const idx = key.indexOf('_');
          if (idx === -1) return null;
          return { booking_id: key.slice(0, idx), created_at: key.slice(idx + 1) };
        })
        .filter(Boolean) as Array<{ booking_id: string; created_at: string }>;
      if (items.length > 0) {
        const batch = items.slice(0, 200);
        markNotificationsReadApi(batch).catch(() => {});
      }
    } catch {
      // corrupt data — just discard
    }
    localStorage.removeItem(LEGACY_NOTIF_READ_KEY);
  }, [user?.user_id]);

  const handleInvalidate = useCallback(
    (event: InvalidateEvent) => {
      if (event.resource === 'unread_messages') {
        if (typeof event.count === 'number') {
          setUnreadDirect(event.count);
        } else {
          refreshUnread();
        }
      } else if (event.resource === 'notifications') {
        void refreshUnreadNotifications();
        window.dispatchEvent(new CustomEvent(NOTIFICATIONS_REFRESH_EVENT));
        if (event.event && event.user_id) {
          window.dispatchEvent(
            new CustomEvent('linkup:user-event', {
              detail: { event: event.event, user_id: event.user_id },
            })
          );
        }
      }
    },
    [setUnreadDirect, refreshUnread, refreshUnreadNotifications]
  );

  const handleUserEvent = useCallback(
    (event: UserEvent) => {
      window.dispatchEvent(new CustomEvent('linkup:user-event', { detail: event }));
      void refreshUnread();
      void refreshUnreadNotifications();
      window.dispatchEvent(new CustomEvent(NOTIFICATIONS_REFRESH_EVENT));
    },
    [refreshUnread, refreshUnreadNotifications]
  );

  useUserEventStream({
    enabled: !!user?.user_id,
    onInvalidate: handleInvalidate,
    onUserEvent: handleUserEvent,
  });

  const value = useMemo<ChatContextValue>(
    () => ({
      openConversationId: state.openConversationId,
      panelConversationId: state.panelConversationId,
      openChat,
      closeChat,
      unreadMessages: state.unreadMessages,
      refreshUnread,
      unreadNotifications: state.unreadNotifications,
      notificationList: state.notificationList,
      notificationsLoading,
      notificationsError,
      markNotificationRead,
      markAllNotificationsRead,
      refreshUnreadNotifications,
      isNotificationRead,
    }),
    [
      state.openConversationId,
      state.panelConversationId,
      state.unreadMessages,
      state.unreadNotifications,
      state.notificationList,
      openChat,
      closeChat,
      refreshUnread,
      notificationsLoading,
      notificationsError,
      markNotificationRead,
      markAllNotificationsRead,
      refreshUnreadNotifications,
      isNotificationRead,
    ]
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
