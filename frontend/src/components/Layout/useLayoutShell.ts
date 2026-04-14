import { useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { useChat } from '../../context/ChatContext';
import { useUserEventStream } from '../../hooks/useUserEventStream';
import type { UserEvent } from '../../types/wsEvents';

export function formatNavBadge(count: number): string | null {
  if (count <= 0) return null;
  return count >= 10 ? '9+' : String(count);
}

export function useLayoutShell() {
  const {
    unreadMessages,
    unreadNotifications,
    openConversationId,
    refreshUnread,
    refreshUnreadNotifications,
  } = useChat();
  const handleUserEvent = useCallback(
    (event: UserEvent) => {
      window.dispatchEvent(new CustomEvent('linkup:user-event', { detail: event }));
      void refreshUnread();
      void refreshUnreadNotifications();
    },
    [refreshUnread, refreshUnreadNotifications]
  );

  useUserEventStream({ onEvent: handleUserEvent });

  const location = useLocation();

  const showChatPopup = Boolean(openConversationId && location.pathname !== '/messages');
  const messagesBadge = formatNavBadge(unreadMessages);
  const notificationsBadge = formatNavBadge(unreadNotifications);

  return {
    openConversationId,
    showChatPopup,
    messagesBadge,
    notificationsBadge,
  };
}
