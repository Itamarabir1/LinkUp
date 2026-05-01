import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { sendMessage } from '../../api/chat';
import { useAuth } from '../../context/AuthContext';
import type { ChatListRow } from '../../types/chatList';
import { getApiErrorMessage, isChatIdempotencyKeyMismatch } from '../../utils/apiError';
import { applyInboundRealMessage, removePendingByClientId } from '../../utils/chatMessagesMerge';
import { consumeOrCreateKey, resetOutboundKey } from '../../utils/outboundIdempotencyKey';
import { apiErr } from '../../utils/i18nError';
import { useConversationMessages } from './useConversationMessages';
import { useChatWebSocket } from './useChatWebSocket';
import { fetchPartnerPresence, type PartnerPresence } from '../../api/presence';

export function useMessageThread(conversationIdOverride?: string) {
  const { conversationId: paramId } = useParams<{ conversationId: string }>();
  const conversationId = conversationIdOverride ?? paramId ?? '';
  const cid = conversationId;

  const { user } = useAuth();

  const {
    conversation,
    messages,
    setMessages,
    messagesHasMore,
    loading,
    loadingMore,
    error,
    setError,
    partnerReadUpToId,
    setConversationRead,
    lastMessageIdRef,
    fetchMissedMessages,
    messagesEndRef,
    loadMoreMessages,
    refreshUnread,
  } = useConversationMessages(cid, user?.user_id);

  const [input, setInput] = useState(() => {
    if (!cid) return '';
    try {
      return localStorage.getItem(`chat_draft_${cid}`) ?? '';
    } catch {
      return '';
    }
  });
  const [partnerTyping, setPartnerTyping] = useState(false);
  const [partnerTypingName, setPartnerTypingName] = useState<string | null>(null);
  const [partnerPresence, setPartnerPresence] = useState<PartnerPresence | null>(null);
  const [sending, setSending] = useState(false);

  const partnerId = conversation?.partner?.user_id;
  const partnerIdRef = useRef(partnerId);
  useEffect(() => {
    partnerIdRef.current = partnerId;
  }, [partnerId]);

  const chatSendIdempotencyKeyRef = useRef<string | null>(null);
  const outboundPendingRef = useRef<{ client_message_id: string; body: string } | null>(null);

  useEffect(() => {
    resetOutboundKey(chatSendIdempotencyKeyRef);
    outboundPendingRef.current = null;
  }, [cid]);

  useEffect(() => {
    setPartnerTyping(false);
    setPartnerTypingName(null);
    setPartnerPresence(null);
    try {
      setInput(cid ? localStorage.getItem(`chat_draft_${cid}`) ?? '' : '');
    } catch {
      setInput('');
    }
  }, [cid]);

  useEffect(() => {
    if (!partnerId) return;
    let cancelled = false;
    fetchPartnerPresence(partnerId)
      .then((res) => {
        if (!cancelled && res.data) setPartnerPresence(res.data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [partnerId]);

  const { sendTypingIfNeeded, sendTypingStop } = useChatWebSocket({
    cid,
    userId: user?.user_id,
    userFullName: user?.full_name,
    refreshUnread,
    partnerIdRef,
    setMessages,
    outboundPendingRef,
    setPartnerTyping,
    setPartnerTypingName,
    setPartnerPresence,
    lastMessageIdRef,
    fetchMissedMessages,
    setConversationRead,
  });

  const recipientId = conversation?.partner?.user_id;

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const body = input.trim();
      if (!body || !cid || sending || !recipientId || !user?.user_id) return;
      setSending(true);
      setError('');
      const client_message_id = crypto.randomUUID();
      outboundPendingRef.current = { client_message_id, body };
      const pendingRow: ChatListRow = {
        kind: 'pending',
        client_message_id,
        conversation_id: cid,
        sender_id: user.user_id,
        body,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, pendingRow]);
      setInput('');
      try {
        localStorage.removeItem(`chat_draft_${cid}`);
      } catch {
        // ignore
      }
      try {
        const key = consumeOrCreateKey(chatSendIdempotencyKeyRef);
        const { data } = await sendMessage(cid, body, key);
        resetOutboundKey(chatSendIdempotencyKeyRef);
        setMessages((prev) =>
          applyInboundRealMessage(prev, data, { dropPendingClientId: client_message_id })
        );
        outboundPendingRef.current = null;
        sendTypingStop(recipientId);
      } catch (err: unknown) {
        if (isChatIdempotencyKeyMismatch(err)) {
          resetOutboundKey(chatSendIdempotencyKeyRef);
        }
        setMessages((prev) => removePendingByClientId(prev, client_message_id));
        outboundPendingRef.current = null;
        setInput(body);
        try {
          localStorage.setItem(`chat_draft_${cid}`, body);
        } catch {
          // ignore
        }
        setError(getApiErrorMessage(err, apiErr('err_send_message')));
      } finally {
        setSending(false);
      }
    },
    [input, cid, sending, recipientId, user?.user_id, setMessages, setError, sendTypingStop]
  );

  const onInputChange = useCallback(
    (val: string) => {
      setInput(val);
      if (cid) {
        try {
          if (val) {
            localStorage.setItem(`chat_draft_${cid}`, val);
          } else {
            localStorage.removeItem(`chat_draft_${cid}`);
          }
        } catch {
          // ignore
        }
      }
      if (recipientId) sendTypingIfNeeded(recipientId);
    },
    [cid, recipientId, sendTypingIfNeeded]
  );

  return {
    cid,
    user,
    conversation,
    messages,
    messagesHasMore,
    loading,
    loadingMore,
    sending,
    error,
    input,
    partnerTyping,
    partnerTypingName,
    partnerPresence,
    partnerReadUpToId,
    messagesEndRef,
    loadMoreMessages,
    handleSend,
    onInputChange,
  };
}

export type MessageThreadViewModel = ReturnType<typeof useMessageThread>;
