import { WS_URLS } from '../config/wsUrls';
import { NotificationRefreshEventSchema } from '../types/wsEvents';
import { useReconnectingWebSocket } from '../hooks/useReconnectingWebSocket';

/**
 * WebSocket גלובלי יחיד להתראות in-app — רענון badge ורשימת התראות.
 */
export function useChatNotificationsWebSocket(
  userId: string | undefined,
  refreshUnreadNotifications: () => Promise<void>,
  refreshUnread: () => Promise<void>
) {
  const onRefresh = () => {
    void refreshUnreadNotifications();
    void refreshUnread();
    window.dispatchEvent(new CustomEvent('linkup-notifications-refresh'));
  };

  useReconnectingWebSocket({
    buildUrl: (token) => WS_URLS.notifications(token),
    enabled: !!userId,
    reconnectKey: userId ?? null,
    reconnectDelayMs: 4000,
    onMessage: (ev) => {
      try {
        const result = NotificationRefreshEventSchema.safeParse(JSON.parse(String(ev.data)) as unknown);
        if (result.success) onRefresh();
      } catch {
        /* ignore */
      }
    },
  });
}
