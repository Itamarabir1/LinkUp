/**
 * ChatContext: פופאפ צ'אט, פנל שיחה במסך הודעות, ומונים להתראות/הודעות.
 * חשוב: ChatProvider חייב להיות בתוך Router (לא עוטף את Router) כדי ש-useLocation() יעבוד.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { api } from '../api/client';
import { getWsBaseUrl } from '../config/env';
import type { NotificationItem } from '../types/api';

const NOTIF_READ_KEY = 'linkup_notif_read';

function getReadSet(): Set<string> {
  try {
    const raw = localStorage.getItem(NOTIF_READ_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

function saveReadSet(set: Set<string>) {
  try {
    localStorage.setItem(NOTIF_READ_KEY, JSON.stringify([...set]));
  } catch {
    // ignore
  }
}

/** מפתח ייחודי לפריט התראה (לlocalStorage + markNotificationRead). */
export function getNotificationItemKey(n: { booking_id: string; created_at: string }): string {
  return `${n.booking_id}_${n.created_at}`;
}

function notificationItemKey(n: { booking_id: string; created_at: string }): string {
  return getNotificationItemKey(n);
}

interface ChatContextValue {
  /** לשימוש בפופאפ — מוצג רק כאשר pathname !== '/messages' */
  openConversationId: string | null;
  /** לשימוש בפנל הימני במסך /messages */
  panelConversationId: string | null;
  openChat: (conversationId: string) => void;
  closeChat: () => void;
  /** מספר שיחות שלא נקראו (לbadge הודעות). */
  unreadMessages: number;
  /** רענון מיידי של מונה הודעות שלא נקראו. */
  refreshUnread: () => void;
  /** מספר התראות שלא נקראו (לbadge התראות). */
  unreadNotifications: number;
  markNotificationRead: (key: string) => void;
  markAllNotificationsRead: () => void;
  refreshUnreadNotifications: () => void;
  /** האם ההתראה עם המפתח הזה סומנה כנקראה (localStorage). */
  isNotificationRead: (key: string) => boolean;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChat must be used within ChatProvider');
  return ctx;
}

interface ChatProviderProps {
  children: ReactNode;
}

export function ChatProvider({ children }: ChatProviderProps) {
  const location = useLocation();
  const { user } = useAuth();
  const [openConversationId, setOpenConversationId] = useState<string | null>(null);
  const [panelConversationId, setPanelConversationId] = useState<string | null>(null);
  const [unreadMessages, setUnreadMessages] = useState(0);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [notificationList, setNotificationList] = useState<NotificationItem[]>([]);

  const refreshUnread = useCallback(async () => {
    if (!user?.user_id) return;
    try {
      const { data } = await api.get<{ count: number }>('/chat/unread-count');
      setUnreadMessages(typeof data?.count === 'number' ? data.count : 0);
    } catch {
      // ignore
    }
  }, [user?.user_id]);

  const openChat = useCallback((conversationId: string) => {
    if (location.pathname === '/messages') {
      setPanelConversationId(conversationId);
      setOpenConversationId(null);
    } else {
      setOpenConversationId(conversationId);
      setPanelConversationId(null);
    }
  }, [location.pathname]);

  const closeChat = useCallback(() => {
    setOpenConversationId(null);
    setPanelConversationId(null);
  }, []);

  const refreshUnreadNotifications = useCallback(async () => {
    try {
      const { data } = await api.get<NotificationItem[]>('/users/me/notifications');
      const list = Array.isArray(data) ? data : [];
      setNotificationList(list);
      const readSet = getReadSet();
      const unread = list.filter((n) => !readSet.has(notificationItemKey(n))).length;
      setUnreadNotifications(unread);
    } catch {
      setUnreadNotifications(0);
      setNotificationList([]);
    }
  }, []);

  const markNotificationRead = useCallback((key: string) => {
    const set = getReadSet();
    set.add(key);
    saveReadSet(set);
    setUnreadNotifications((c) => Math.max(0, c - 1));
  }, []);

  const markAllNotificationsRead = useCallback(() => {
    const set = getReadSet();
    notificationList.forEach((n) => set.add(notificationItemKey(n)));
    saveReadSet(set);
    setUnreadNotifications(0);
  }, [notificationList]);

  const isNotificationRead = useCallback((key: string) => getReadSet().has(key), []);

  useEffect(() => {
    if (!user?.user_id) {
      queueMicrotask(() => {
        setUnreadMessages(0);
        setUnreadNotifications(0);
        setNotificationList([]);
      });
      return;
    }
    queueMicrotask(() => refreshUnreadNotifications());
    const interval = setInterval(refreshUnreadNotifications, 30000);
    return () => clearInterval(interval);
  }, [user?.user_id, refreshUnreadNotifications]);

  /** WebSocket גלובלי יחיד להתראות in-app — רענון badge ורשימת התראות. */
  useEffect(() => {
    if (!user?.user_id) return;
    const token = localStorage.getItem('linkup_access_token');
    if (!token) return;
    const url = `${getWsBaseUrl()}/notifications/ws?token=${encodeURIComponent(token)}`;
    let ws: WebSocket | null = null;
    let closed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const onRefresh = () => {
      void refreshUnreadNotifications();
      // Keep message badge reasonably fresh from a single global socket flow.
      void refreshUnread();
      window.dispatchEvent(new CustomEvent('linkup-notifications-refresh'));
    };

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(url);
      } catch {
        reconnectTimer = setTimeout(connect, 5000);
        return;
      }
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data)) as { type?: string };
          if (msg?.type === 'notifications_refresh') onRefresh();
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        ws = null;
        if (!closed) reconnectTimer = setTimeout(connect, 4000);
      };
      ws.onerror = () => {
        try {
          ws?.close();
        } catch {
          /* ignore */
        }
      };
    };
    connect();
    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      try {
        ws?.close();
      } catch {
        /* ignore */
      }
    };
  }, [user?.user_id, refreshUnreadNotifications, refreshUnread]);

  useEffect(() => {
    if (!user?.user_id) return;
    void refreshUnread();
    const interval = setInterval(refreshUnread, 30000);
    return () => clearInterval(interval);
  }, [user?.user_id, refreshUnread]);

  const value = useMemo<ChatContextValue>(
    () => ({
      openConversationId,
      panelConversationId,
      openChat,
      closeChat,
      unreadMessages,
      refreshUnread,
      unreadNotifications,
      markNotificationRead,
      markAllNotificationsRead,
      refreshUnreadNotifications,
      isNotificationRead,
    }),
    [
      openConversationId,
      panelConversationId,
      openChat,
      closeChat,
      unreadMessages,
      refreshUnread,
      unreadNotifications,
      markNotificationRead,
      markAllNotificationsRead,
      refreshUnreadNotifications,
      isNotificationRead,
    ]
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
