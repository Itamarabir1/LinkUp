import { useEffect, useRef } from 'react';
import { getWsToken } from '../config/wsUrls';

interface Options {
  buildUrl: (token: string) => string;
  enabled?: boolean;
  reconnectDelayMs?: number;
  onMessage: (ev: MessageEvent) => void;
  /** Called after a successful connection (including reconnect). */
  onOpen?: () => void;
  /** Reconnect key (e.g. rideId); changing it reconnects to a new URL. */
  reconnectKey?: string | null;
}

/**
 */
export function useReconnectingWebSocket({
  buildUrl,
  enabled = true,
  reconnectDelayMs = 3000,
  onMessage,
  onOpen,
  reconnectKey,
}: Options) {
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const buildUrlRef = useRef(buildUrl);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  useEffect(() => {
    onOpenRef.current = onOpen;
  }, [onOpen]);
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

      ws.onopen = () => {
        onOpenRef.current?.();
      };
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
