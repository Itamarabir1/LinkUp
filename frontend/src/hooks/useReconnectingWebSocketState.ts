import { useEffect, useRef, useState } from 'react';
import { getWsToken } from '../config/wsUrls';

interface Options {
  buildUrl: (token: string) => string;
  enabled?: boolean;
  reconnectDelayMs?: number;
  connectionErrorLabel?: string;
  onMessage: (ev: MessageEvent) => void;
  onReset?: () => void;
  /** Reconnect key (e.g. rideId/bookingId); changing it reconnects. */
  reconnectKey?: string | null;
}

interface State {
  connected: boolean;
  error: string | null;
}

/**
 * WebSocket גנרי עם reconnect + connected/error state.
 * buildUrl נשמר ב-ref כדי לא לגרום ל-reconnect בכל render.
 */
export function useReconnectingWebSocketState({
  buildUrl,
  enabled = true,
  reconnectDelayMs = 3000,
  connectionErrorLabel,
  onMessage,
  onReset,
  reconnectKey,
}: Options): State {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onMessageRef = useRef(onMessage);
  const onResetRef = useRef(onReset);
  const buildUrlRef = useRef(buildUrl);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  useEffect(() => {
    onResetRef.current = onReset;
  }, [onReset]);
  useEffect(() => {
    buildUrlRef.current = buildUrl;
  }, [buildUrl]);

  useEffect(() => {
    if (!enabled) {
      queueMicrotask(() => {
        setConnected(false);
        setError(null);
        onResetRef.current?.();
      });
      return;
    }

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
        setError(null);
        setConnected(true);
      };
      ws.onmessage = (ev) => onMessageRef.current(ev);
      ws.onclose = () => {
        setConnected(false);
        ws = null;
        if (!cancelled) reconnectTimer = setTimeout(connect, reconnectDelayMs);
      };
      ws.onerror = () => {
        if (connectionErrorLabel) setError(connectionErrorLabel);
        ws?.close();
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      onResetRef.current?.();
    };
  }, [enabled, reconnectDelayMs, connectionErrorLabel, reconnectKey]);

  return { connected, error };
}
