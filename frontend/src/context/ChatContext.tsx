/**
 * ChatContext: פופאפ צ'אט, פנל שיחה במסך הודעות, ומונים להתראות/הודעות.
 * חשוב: ChatProvider חייב להיות בתוך Router (לא עוטף את Router) כדי ש-useLocation() יעבוד.
 */
import { createContext, useContext, useMemo, useReducer } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import type { ChatContextValue, ChatProviderProps } from './chatContext.types';
import { chatReducer, initialChatState } from './chatState';
import { useChatNotificationsFeed } from './useChatNotificationsFeed';
import { useChatNotificationsWebSocket } from './useChatNotificationsWebSocket';
import { useChatOpenClose } from './useChatOpenClose';
import { useChatUnreadMessages } from './useChatUnreadMessages';

export { getNotificationItemKey } from './chatNotificationStorage';

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
  const refreshUnread = useChatUnreadMessages(user?.user_id, dispatch);

  const {
    refreshUnreadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    isNotificationRead,
    notificationsLoading,
    notificationsError,
  } = useChatNotificationsFeed(user?.user_id, state.notificationList, dispatch);

  useChatNotificationsWebSocket(user?.user_id, refreshUnreadNotifications, refreshUnread);

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
