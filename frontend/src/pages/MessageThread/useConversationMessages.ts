import { useCallback, useEffect, useRef, useState } from 'react';
import { getConversation, getMessages, markConversationRead } from '../../api/chat';
import type { ConversationDetail, MessageResponse } from '../../types/api';
import { useChat } from '../../context/ChatContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { apiErr } from '../../utils/i18nError';

export function useConversationMessages(cid: string, userId: string | undefined) {
  const { refreshUnread } = useChat();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [messagesNextCursor, setMessagesNextCursor] = useState<string | null>(null);
  const [messagesHasMore, setMessagesHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchConversation = useCallback(async () => {
    if (!cid || !userId) return;
    setLoading(true);
    setError('');
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(cid),
        getMessages(cid, { limit: 30 }),
      ]);
      setConversation(convRes.data);
      const paginated = msgRes.data;
      setMessages(paginated?.items ?? []);
      setMessagesNextCursor(paginated?.next_cursor ?? null);
      setMessagesHasMore(paginated?.has_more ?? false);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_load_conversation')));
    } finally {
      setLoading(false);
    }
  }, [cid, userId]);

  const loadMoreMessages = useCallback(async () => {
    if (!cid || !messagesNextCursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const msgRes = await getMessages(cid, { limit: 30, before: parseInt(messagesNextCursor, 10) });
      const paginated = msgRes.data;
      const older = paginated?.items ?? [];
      setMessages((prev) => [...older, ...prev]);
      setMessagesNextCursor(paginated?.next_cursor ?? null);
      setMessagesHasMore(paginated?.has_more ?? false);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_load_older_messages')));
    } finally {
      setLoadingMore(false);
    }
  }, [cid, messagesNextCursor, loadingMore]);

  useEffect(() => {
    fetchConversation();
  }, [fetchConversation]);

  useEffect(() => {
    if (!cid) return;
    void markConversationRead(cid)
      .then(() => refreshUnread())
      .catch(() => {});
  }, [cid, refreshUnread]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return {
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
  };
}
