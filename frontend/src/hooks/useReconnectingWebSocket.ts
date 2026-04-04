import { useEffect, useRef } from 'react';
import { getWsToken } from '../config/wsUrls';

interface Options {
  buildUrl: (token: string) => string;
  enabled?: boolean;
  reconnectDelayMs?: number;
  onMessage: (ev: MessageEvent) => void;
  /** כשמשתנה (למשל rideId) — ה-effect מתחבר מחדש ל-URL הנכון */
  reconnectKey?: string | null;
}

/**
 * WebSocket גנרי עם reconnect אוטומטי — read-only, ללא state.
 * buildUrl נשמר ב-ref כדי לא לגרום ל-reconnect בכל render.
 */
export function useReconnectingWebSocket({
  buildUrl,
  enabled = true,
  reconnectDelayMs = 3000,
  onMessage,
  reconnectKey,
}: Options) {
  const onMessageRef = useRef(onMessage);
  const buildUrlRef = useRef(buildUrl);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  useEffect(() => {
    buildUrlRef.current = buildUrl;
  }, [buildUrl]);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      const token = getWsToken();
      if (!token) return;

      try {
        ws = new WebSocket(buildUrlRef.current(token));
      } catch {
        if (!cancelled) reconnectTimer = setTimeout(connect, reconnectDelayMs);
        return;
      }

      ws.onmessage = (ev) => onMessageRef.current(ev);
      ws.onclose = () => {
        ws = null;
        if (!cancelled) reconnectTimer = setTimeout(connect, reconnectDelayMs);
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [enabled, reconnectDelayMs, reconnectKey]);
}
