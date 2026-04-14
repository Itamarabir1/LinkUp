import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import { getConversation, getMessages, sendMessage } from '../../api/chat';
import type { ConversationDetail, MessageResponse } from '../../types/api';
import { getApiErrorMessage } from '../../utils/apiError';
import { apiErr } from '../../utils/i18nError';

export function useChatPopup(conversationId: string) {
  const { user } = useAuth();
  const { closeChat } = useChat();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const [fetchError, setFetchError] = useState('');
  const [sendError, setSendError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    if (!conversationId || !user?.user_id) return;
    setLoading(true);
    setFetchError('');
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(conversationId),
        getMessages(conversationId, { limit: 30 }),
      ]);
      setConversation(convRes.data);
      setMessages(msgRes.data?.items ?? []);
    } catch (err) {
      setFetchError(getApiErrorMessage(err, apiErr('err_load_chat_popup_fetch')));
      setConversation(null);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [conversationId, user?.user_id]);

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
      if (!body || !conversationId || sending) return;
      setSending(true);
      setSendError('');
      setInput('');
      try {
        const { data } = await sendMessage(conversationId, body);
        setMessages((prev) => [...prev, data]);
      } catch (err) {
        setSendError(getApiErrorMessage(err, apiErr('err_load_chat_popup_send')));
        setInput(body);
      } finally {
        setSending(false);
      }
    },
    [conversationId, input, sending]
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
