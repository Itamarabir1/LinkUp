import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import { getConversation, getMessages, sendMessage } from '../../api/chat';
import type { ConversationDetail } from '../../types/api';
import type { ChatListRow } from '../../types/chatList';
import { toConfirmedRows } from '../../types/chatList';
import { getApiErrorMessage, isChatIdempotencyKeyMismatch } from '../../utils/apiError';
import { applyInboundRealMessage, removePendingByClientId } from '../../utils/chatMessagesMerge';
import { consumeOrCreateKey, resetOutboundKey } from '../../utils/outboundIdempotencyKey';
import { apiErr } from '../../utils/i18nError';
import { useAbortSignal } from '../../hooks/useAbortSignal';

export function useChatPopup(conversationId: string) {
  const { user } = useAuth();
  const { closeChat } = useChat();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<ChatListRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const [fetchError, setFetchError] = useState('');
  const [sendError, setSendError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const chatSendIdempotencyKeyRef = useRef<string | null>(null);

  useEffect(() => {
    resetOutboundKey(chatSendIdempotencyKeyRef);
  }, [conversationId]);

  const getSignal = useAbortSignal();

  const fetchData = useCallback(async () => {
    if (!conversationId || !user?.user_id) return;
    const signal = getSignal();
    setLoading(true);
    setFetchError('');
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(conversationId, { signal }),
        getMessages(conversationId, { limit: 30, signal }),
      ]);
      setConversation(convRes.data);
      setMessages(toConfirmedRows(msgRes.data?.items ?? []));
    } catch (err) {
      if (axios.isCancel(err)) return;
      setFetchError(getApiErrorMessage(err, apiErr('err_load_chat_popup_fetch')));
      setConversation(null);
      setMessages([]);
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [conversationId, user?.user_id, getSignal]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const setInputFromUi = useCallback((value: string) => {
    setSendError('');
    setInput(value);
  }, []);

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const body = input.trim();
      if (!body || !conversationId || sending || !user?.user_id) return;
      setSending(true);
      setSendError('');
      const client_message_id = crypto.randomUUID();
      const pendingRow: ChatListRow = {
        kind: 'pending',
        client_message_id,
        conversation_id: conversationId,
        sender_id: user.user_id,
        body,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, pendingRow]);
      setInput('');
      try {
        const key = consumeOrCreateKey(chatSendIdempotencyKeyRef);
        const { data } = await sendMessage(conversationId, body, key);
        resetOutboundKey(chatSendIdempotencyKeyRef);
        setMessages((prev) =>
          applyInboundRealMessage(prev, data, { dropPendingClientId: client_message_id })
        );
      } catch (err: unknown) {
        if (isChatIdempotencyKeyMismatch(err)) {
          resetOutboundKey(chatSendIdempotencyKeyRef);
        }
        setMessages((prev) => removePendingByClientId(prev, client_message_id));
        setSendError(getApiErrorMessage(err, apiErr('err_load_chat_popup_send')));
        setInput(body);
      } finally {
        setSending(false);
      }
    },
    [conversationId, input, sending, user?.user_id]
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend(e as unknown as React.FormEvent);
    }
  };

  const handleMaximize = () => {
    navigate(`/messages/${conversationId}`);
    closeChat();
  };

  return {
    user,
    closeChat,
    conversation,
    messages,
    loading,
    sending,
    fetchError,
    sendError,
    input,
    setInput: setInputFromUi,
    messagesEndRef,
    listRef,
    handleSend,
    onKeyDown,
    handleMaximize,
  };
}
