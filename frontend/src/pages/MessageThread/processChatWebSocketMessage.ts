import type { MutableRefObject } from 'react';
import { markConversationRead } from '../../api/chat';
import type { PartnerPresence } from '../../api/presence';
import type { MessageResponse } from '../../types/api';
import type { ChatListRow } from '../../types/chatList';
import { ChatMessageSchema, ChatPresenceEventSchema, MessageReadEventSchema } from '../../types/wsEvents';
import { applyInboundRealMessage } from '../../utils/chatMessagesMerge';
import { TYPING_DISPLAY_TIMEOUT_MS } from './messageThread.constants';

export type OutboundPendingRef = MutableRefObject<{
  client_message_id: string;
  body: string;
} | null>;

export interface ChatWebSocketProcessContext {
  cid: string;
  userId: string | undefined;
  refreshUnread: () => void;
  partnerIdRef: MutableRefObject<string | undefined>;
  setMessages: React.Dispatch<React.SetStateAction<ChatListRow[]>>;
  setPartnerTyping: React.Dispatch<React.SetStateAction<boolean>>;
  setPartnerTypingName: React.Dispatch<React.SetStateAction<string | null>>;
  setPartnerPresence: React.Dispatch<React.SetStateAction<PartnerPresence | null>>;
  typingHideTimeoutRef: MutableRefObject<ReturnType<typeof setTimeout> | null>;
  setConversationRead: (readUpToId: number) => void;
  outboundPendingRef: OutboundPendingRef;
  requestScrollToBottom?: () => void;
}

/**
 * Process a single JSON frame from the chat WebSocket
 * (typing, unread count, incoming message, read receipts).
 */
export function processChatWebSocketMessage(
  data: Record<string, unknown>,
  ctx: ChatWebSocketProcessContext
): void {
  const presenceResult = ChatPresenceEventSchema.safeParse(data);

  if (presenceResult.success) {
    const event = presenceResult.data;

    if (event.type === 'user_online') {
      if (event.user_id === ctx.partnerIdRef.current) {
        ctx.setPartnerPresence((prev) => ({
          online: true,
          last_seen: prev?.last_seen ?? null,
        }));
      }
      return;
    }

    if (event.type === 'user_offline') {
      if (event.user_id === ctx.partnerIdRef.current) {
        ctx.setPartnerPresence((prev) => ({
          online: false,
          last_seen: prev?.last_seen ?? null,
        }));
      }
      return;
    }

    if (event.type === 'unread_count') {
      void ctx.refreshUnread();
      return;
    }

    if (
      event.type === 'typing_start' &&
      event.user_id !== ctx.userId &&
      event.conversation_id === ctx.cid
    ) {
      ctx.setPartnerTyping(true);
      ctx.setPartnerTypingName(event.full_name ?? null);
      if (ctx.typingHideTimeoutRef.current) clearTimeout(ctx.typingHideTimeoutRef.current);
      ctx.typingHideTimeoutRef.current = setTimeout(() => {
        ctx.setPartnerTyping(false);
        ctx.setPartnerTypingName(null);
        ctx.typingHideTimeoutRef.current = null;
      }, TYPING_DISPLAY_TIMEOUT_MS);
      return;
    }

    if (
      event.type === 'typing_stop' &&
      event.user_id !== ctx.userId &&
      event.conversation_id === ctx.cid
    ) {
      ctx.setPartnerTyping(false);
      ctx.setPartnerTypingName(null);
      if (ctx.typingHideTimeoutRef.current) {
        clearTimeout(ctx.typingHideTimeoutRef.current);
        ctx.typingHideTimeoutRef.current = null;
      }
      return;
    }
  }

  const msgResult = ChatMessageSchema.safeParse(data);
  if (msgResult.success) {
    const d = msgResult.data;
    if (d.conversation_id !== ctx.cid) return;
    const msg: MessageResponse = {
      message_id: d.message_id,
      conversation_id: d.conversation_id,
      sender_id: d.sender_id,
      body: d.body,
      created_at: d.created_at,
    };
    void markConversationRead(ctx.cid)
      .then(() => ctx.refreshUnread())
      .catch(() => {});

    const isOwn = msg.sender_id === ctx.userId;
    const pending = ctx.outboundPendingRef.current;
    const dropPendingClientId =
      isOwn && pending ? pending.client_message_id : null;

    ctx.requestScrollToBottom?.();
    ctx.setMessages((prev) => {
      const next = applyInboundRealMessage(prev, msg, { dropPendingClientId });
      return next;
    });

    if (isOwn && dropPendingClientId) {
      ctx.outboundPendingRef.current = null;
    }

    if (msg.sender_id !== ctx.userId) ctx.setPartnerTyping(false);
    return;
  }

  const msgReadResult = MessageReadEventSchema.safeParse(data);
  if (msgReadResult.success) {
    const e = msgReadResult.data;
    if (
      e.conversation_id === ctx.cid &&
      e.reader_id !== ctx.userId &&
      e.read_up_to_message_id !== undefined
    ) {
      ctx.setConversationRead(e.read_up_to_message_id);
    }
  }
}
