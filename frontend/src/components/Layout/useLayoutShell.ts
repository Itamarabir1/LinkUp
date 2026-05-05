import { useLocation } from 'react-router-dom';
import { useChat } from '../../context/ChatContext';

export function formatNavBadge(count: number): string | null {
  if (count <= 0) return null;
  return count >= 10 ? '9+' : String(count);
}

export function useLayoutShell() {
  const { unreadMessages, unreadNotifications, openConversationId } = useChat();

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
