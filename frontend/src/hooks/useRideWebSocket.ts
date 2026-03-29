import { useEffect, useRef } from 'react';
import { getRideWebSocketUrl } from '../config/env';
import { RideEventSchema, type RideEvent } from '../types/wsEvents';

interface Options {
  rideId: string | null;
  onMessage: (msg: RideEvent) => void;
  enabled?: boolean;
}

/**
 * WebSocket גנרי לאירועי סטטוס נסיעה — עם reconnect אוטומטי.
 */
export function useRideWebSocket({ rideId, onMessage, enabled = true }: Options) {
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    if (!rideId || !enabled) return;
    const token = localStorage.getItem('linkup_access_token');
    if (!token) return;

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      ws = new WebSocket(getRideWebSocketUrl(rideId, token));

      ws.onmessage = (ev) => {
        try {
          const raw = JSON.parse(ev.data as string);
          const result = RideEventSchema.safeParse(raw);
          if (!result.success) {
            console.warn('[useRideWebSocket] unexpected payload:', raw, result.error.flatten());
            return;
          }
          onMessageRef.current(result.data);
        } catch {
          /* ignore malformed JSON */
        }
      };

      ws.onclose = () => {
        ws = null;
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws?.close();
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [rideId, enabled]);
}
