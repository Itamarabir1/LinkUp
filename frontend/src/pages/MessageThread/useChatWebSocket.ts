import { useCallback, useEffect, useRef } from 'react';
import type { MessageResponse } from '../../types/api';
import { STORAGE_KEYS } from '../../config/constants';
import { getChatWebSocketUrl } from '../../config/env';
import type { PartnerPresence } from '../../api/presence';
import { TYPING_THROTTLE_MS } from './messageThread.constants';
import { processChatWebSocketMessage } from './processChatWebSocketMessage';

/**
 * WebSocket לצ'אט: הודעות בזמן אמת, הקלדה, unread, נוכחות.
 */
export function useChatWebSocket(options: {
  cid: string;
  userId: string | undefined;
  userFullName: string | undefined;
  refreshUnread: () => void;
  partnerIdRef: React.MutableRefObject<string | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<MessageResponse[]>>;
  setPartnerTyping: React.Dispatch<React.SetStateAction<boolean>>;
  setPartnerTypingName: React.Dispatch<React.SetStateAction<string | null>>;
  setPartnerPresence: React.Dispatch<React.SetStateAction<PartnerPresence | null>>;
}) {
  const {
    cid,
    userId,
    userFullName,
    refreshUnread,
    partnerIdRef,
    setMessages,
    setPartnerTyping,
    setPartnerTypingName,
    setPartnerPresence,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const lastTypingSentRef = useRef(0);
  const typingHideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ type: 'ping' }));
        } catch {
          // ignore
        }
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [cid]);

  useEffect(() => {
    if (!cid) return;
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const scheduleReconnect = () => {
      if (cancelled) return;
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, 3000);
    };

    const connect = () => {
      const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
      if (!token || cancelled) return;

      const url = getChatWebSocketUrl(token);
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const chunks = String(event.data).split('\n');
        for (const line of chunks) {
          if (!line.trim()) continue;
          let data: Record<string, unknown>;
          try {
            data = JSON.parse(line) as Record<string, unknown>;
          } catch {
            continue;
          }
          processChatWebSocketMessage(data, {
            cid,
            userId,
            refreshUnread,
            partnerIdRef,
            setMessages,
            setPartnerTyping,
            setPartnerTypingName,
            setPartnerPresence,
            typingHideTimeoutRef,
          });
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        if (!cancelled) {
          scheduleReconnect();
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (typingHideTimeoutRef.current) {
        clearTimeout(typingHideTimeoutRef.current);
        typingHideTimeoutRef.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [
    cid,
    userId,
    refreshUnread,
    partnerIdRef,
    setMessages,
    setPartnerTyping,
    setPartnerTypingName,
    setPartnerPresence,
  ]);

  const sendTypingIfNeeded = useCallback(
    (recipientId: string) => {
      if (!cid || !userId) return;
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const now = Date.now();
      if (now - lastTypingSentRef.current < TYPING_THROTTLE_MS) return;
      lastTypingSentRef.current = now;
      try {
        ws.send(
          JSON.stringify({
            type: 'typing_start',
            conversation_id: cid,
            recipient_id: recipientId,
            full_name: userFullName ?? undefined,
          })
        );
      } catch {
        // ignore
      }
    },
    [cid, userId, userFullName]
  );

  const sendTypingStop = useCallback(
    (recipientId: string) => {
      if (!cid || !userId) return;
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      lastTypingSentRef.current = 0;
      try {
        ws.send(
          JSON.stringify({
            type: 'typing_stop',
            conversation_id: cid,
            recipient_id: recipientId,
            full_name: userFullName ?? undefined,
          })
        );
      } catch {
        // ignore
      }
    },
    [cid, userId, userFullName]
  );

  return { sendTypingIfNeeded, sendTypingStop };
}
