import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import { initFCM } from '../../services/fcm';
import { useUserEventStream } from '../../hooks/useUserEventStream';
import type { UserEvent } from '../../types/wsEvents';

export function formatNavBadge(count: number): string | null {
  if (count <= 0) return null;
  return count >= 10 ? '9+' : String(count);
}

export function useLayoutShell() {
  const { logout } = useAuth();
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

  const navigate = useNavigate();
  const location = useLocation();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission | null>(
    'Notification' in window ? Notification.permission : null
  );

  const showChatPopup = Boolean(openConversationId && location.pathname !== '/messages');
  const messagesBadge = formatNavBadge(unreadMessages);
  const notificationsBadge = formatNavBadge(unreadNotifications);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setProfileOpen(false);
    await logout();
    navigate('/login', { replace: true });
  };

  const handleEnableNotifications = async () => {
    await initFCM();
    setNotifPermission(Notification.permission);
    setProfileOpen(false);
  };

  return {
    openConversationId,
    showChatPopup,
    messagesBadge,
    notificationsBadge,
    profileOpen,
    setProfileOpen,
    profileRef,
    notifPermission,
    handleLogout,
    handleEnableNotifications,
  };
}
