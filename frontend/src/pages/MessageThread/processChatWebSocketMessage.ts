import type { MutableRefObject } from 'react';
import { markConversationRead } from '../../api/chat';
import type { PartnerPresence } from '../../api/presence';
import type { MessageResponse } from '../../types/api';
import { TYPING_DISPLAY_TIMEOUT_MS } from './messageThread.constants';

export interface ChatWebSocketProcessContext {
  cid: string;
  userId: string | undefined;
  refreshUnread: () => void;
  partnerIdRef: MutableRefObject<string | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<MessageResponse[]>>;
  setPartnerTyping: React.Dispatch<React.SetStateAction<boolean>>;
  setPartnerTypingName: React.Dispatch<React.SetStateAction<string | null>>;
  setPartnerPresence: React.Dispatch<React.SetStateAction<PartnerPresence | null>>;
  typingHideTimeoutRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
}

/**
 * מעבד הודעת JSON אחת מ־WebSocket הצ'אט (typing, unread, הודעה חדשה וכו').
 */
export function processChatWebSocketMessage(
  data: Record<string, unknown>,
  ctx: ChatWebSocketProcessContext
): void {
  const {
    cid,
    userId,
    refreshUnread,
    partnerIdRef,
    setMessages,
    setPartnerTyping,
    setPartnerTypingName,
    setPartnerPresence,
    typingHideTimeoutRef,
  } = ctx;

  if (data?.type === 'user_offline') {
    const uid = String(data.user_id ?? '');
    if (uid && uid === partnerIdRef.current) {
      setPartnerPresence((prev) => ({
        online: false,
        last_seen: prev?.last_seen ?? null,
      }));
    }
    return;
  }
  if (data?.type === 'unread_count') {
    void refreshUnread();
    return;
  }
  if (typeof data?.message_id === 'number' && data?.conversation_id === cid) {
    void markConversationRead(cid)
      .then(() => refreshUnread())
      .catch(() => {});
  }
  if (data?.type === 'typing_start' && data?.user_id !== userId) {
    setPartnerTyping(true);
    setPartnerTypingName((data.full_name as string) || null);
    if (typingHideTimeoutRef.current) clearTimeout(typingHideTimeoutRef.current);
    typingHideTimeoutRef.current = setTimeout(() => {
      setPartnerTyping(false);
      setPartnerTypingName(null);
      typingHideTimeoutRef.current = null;
    }, TYPING_DISPLAY_TIMEOUT_MS);
    return;
  }
  if (
    data?.type === 'typing_stop' &&
    data?.conversation_id === cid &&
    data?.user_id !== userId
  ) {
    setPartnerTyping(false);
    setPartnerTypingName(null);
    if (typingHideTimeoutRef.current) {
      clearTimeout(typingHideTimeoutRef.current);
      typingHideTimeoutRef.current = null;
    }
    return;
  }
  if (typeof (data as unknown as MessageResponse).message_id === 'number') {
    const msg = data as unknown as MessageResponse;
    setMessages((prev) => [...prev, msg]);
    if (msg.sender_id !== userId) setPartnerTyping(false);
  }
}
