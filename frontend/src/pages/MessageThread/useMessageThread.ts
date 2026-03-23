import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { sendMessage } from '../../api/chat';
import { useAuth } from '../../context/AuthContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { useConversationMessages } from './useConversationMessages';
import { useChatWebSocket } from './useChatWebSocket';
import { usePartnerPresencePolling, type PartnerPresence } from './usePartnerPresencePolling';

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

  usePartnerPresencePolling(partnerId, setPartnerPresence);

  const { sendTypingIfNeeded, sendTypingStop } = useChatWebSocket({
    cid,
    userId: user?.user_id,
    userFullName: user?.full_name,
    refreshUnread,
    partnerIdRef,
    setMessages,
    setPartnerTyping,
    setPartnerTypingName,
    setPartnerPresence,
  });

  const recipientId = conversation?.partner?.user_id;

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const body = input.trim();
      if (!body || !cid || sending || !recipientId) return;
      setSending(true);
      setError('');
      try {
        const { data } = await sendMessage(cid, body);
        setMessages((prev) => [...prev, data]);
        setInput('');
        try {
          localStorage.removeItem(`chat_draft_${cid}`);
        } catch {
          // ignore
        }
        sendTypingStop(recipientId);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, 'שליחת ההודעה נכשלה'));
      } finally {
        setSending(false);
      }
    },
    [input, cid, sending, recipientId, setMessages, setError, sendTypingStop]
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
    messagesEndRef,
    loadMoreMessages,
    handleSend,
    onInputChange,
  };
}

export type MessageThreadViewModel = ReturnType<typeof useMessageThread>;
