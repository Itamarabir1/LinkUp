import { useEffect } from 'react';
import { getWsBaseUrl } from '../config/env';
import { NotificationRefreshEventSchema } from '../types/wsEvents';

/**
 * WebSocket גלובלי יחיד להתראות in-app — רענון badge ורשימת התראות.
 */
export function useChatNotificationsWebSocket(
  userId: string | undefined,
  refreshUnreadNotifications: () => Promise<void>,
  refreshUnread: () => Promise<void>
) {
  useEffect(() => {
    if (!userId) return;
    const token = localStorage.getItem('linkup_access_token');
    if (!token) return;
    const url = `${getWsBaseUrl()}/notifications/ws?token=${encodeURIComponent(token)}`;
    let ws: WebSocket | null = null;
    let closed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const onRefresh = () => {
      void refreshUnreadNotifications();
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
          const raw = JSON.parse(String(ev.data)) as unknown;
          const result = NotificationRefreshEventSchema.safeParse(raw);
          if (result.success) onRefresh();
        } catch {
          // ignore malformed JSON
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
  }, [userId, refreshUnreadNotifications, refreshUnread]);
}
