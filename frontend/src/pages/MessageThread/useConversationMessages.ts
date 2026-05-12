import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { getConversation, getMessages, markConversationRead } from '../../api/chat';
import type { ConversationDetail, MessageResponse } from '../../types/api';
import type { ChatListRow } from '../../types/chatList';
import { isConfirmedRow, toConfirmedRows } from '../../types/chatList';
import { useChat } from '../../context/ChatContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { apiErr } from '../../utils/i18nError';
import { useAbortSignal } from '../../hooks/useAbortSignal';
import { fetchMissedGap } from './fetchMissedGap';

function confirmedMessages(rows: ChatListRow[]): MessageResponse[] {
  return rows.filter(isConfirmedRow).map((r) => r.message);
}

/** Contiguous pending row(s) at the end of the list only (optimistic outbound). */
function pendingTail(rows: ChatListRow[]): ChatListRow[] {
  let start = rows.length;
  for (let j = rows.length - 1; j >= 0; j--) {
    if (rows[j].kind === 'pending') start = j;
    else break;
  }
  return start === rows.length ? [] : rows.slice(start);
}

function mergeConfirmedWithTail(
  mergedReals: MessageResponse[],
  tail: ChatListRow[]
): ChatListRow[] {
  return [...toConfirmedRows(mergedReals), ...tail];
}

export function useConversationMessages(cid: string, userId: string | undefined) {
  const { refreshUnread } = useChat();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<ChatListRow[]>([]);
  const [messagesNextCursor, setMessagesNextCursor] = useState<string | null>(null);
  const [messagesHasMore, setMessagesHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [partnerReadUpToId, setPartnerReadUpToId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastMessageIdRef = useRef<number | null>(null);
  const isFetchingMissedRef = useRef(false);
  const cidRef = useRef(cid);
  const getFetchSignal = useAbortSignal();
  const getLoadMoreSignal = useAbortSignal();

  const fetchConversation = useCallback(async () => {
    if (!cid || !userId) return;
    const signal = getFetchSignal();
    setLoading(true);
    setError('');
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(cid, { signal }),
        getMessages(cid, { limit: 30, signal }),
      ]);
      setConversation(convRes.data);
      const paginated = msgRes.data;
      setMessages(toConfirmedRows(paginated?.items ?? []));
      setMessagesNextCursor(paginated?.next_cursor ?? null);
      setMessagesHasMore(paginated?.has_more ?? false);
    } catch (err: unknown) {
      if (axios.isCancel(err)) return;
      setError(getApiErrorMessage(err, apiErr('err_load_conversation')));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [cid, userId, getFetchSignal]);

  const loadMoreMessages = useCallback(async () => {
    if (!cid || !messagesNextCursor || loadingMore) return;
    const signal = getLoadMoreSignal();
    setLoadingMore(true);
    try {
      const msgRes = await getMessages(cid, { limit: 30, after: messagesNextCursor, signal });
      const paginated = msgRes.data;
      const older = paginated?.items ?? [];
      setMessages((prev) => [...toConfirmedRows(older), ...prev]);
      setMessagesNextCursor(paginated?.next_cursor ?? null);
      setMessagesHasMore(paginated?.has_more ?? false);
    } catch (err: unknown) {
      if (axios.isCancel(err)) return;
      setError(getApiErrorMessage(err, apiErr('err_load_older_messages')));
    } finally {
      if (!signal.aborted) setLoadingMore(false);
    }
  }, [cid, messagesNextCursor, loadingMore, getLoadMoreSignal]);

  const fetchMissedMessages = useCallback(
    async (afterMessageId: number) => {
      if (!cid || isFetchingMissedRef.current) return;
      isFetchingMissedRef.current = true;
      const startedCid = cid;
      try {
        const { messages: newMsgs } = await fetchMissedGap(cid, afterMessageId, {
          shouldAbort: () => cidRef.current !== startedCid,
        });
        if (newMsgs.length === 0) return;
        setMessages((prev) => {
          if (cidRef.current !== startedCid) return prev;
          const tail = pendingTail(prev);
          const reals = confirmedMessages(prev);
          const existingIds = new Set(reals.map((m) => m.message_id));
          const toAdd = newMsgs.filter((m) => !existingIds.has(m.message_id));
          if (toAdd.length === 0) return prev;
          const mergedReals = [...reals, ...toAdd].sort((a, b) => a.message_id - b.message_id);
          return mergeConfirmedWithTail(mergedReals, tail);
        });
      } catch {
        // ignore reconnect backfill errors
      } finally {
        isFetchingMissedRef.current = false;
      }
    },
    [cid]
  );

  useEffect(() => {
    cidRef.current = cid;
  }, [cid]);

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
    setPartnerReadUpToId(null);
  }, [cid]);

  useEffect(() => {
    const reals = confirmedMessages(messages);
    const maxId = reals.reduce((max, m) => Math.max(max, m.message_id), 0);
    lastMessageIdRef.current = reals.length > 0 ? maxId : null;
  }, [messages]);

  useEffect(() => {
    const id = conversation?.partner_read_up_to_message_id;
    if (id == null) return;
    setPartnerReadUpToId((prev) => (prev !== null ? Math.max(prev, id) : id));
  }, [conversation?.partner_read_up_to_message_id]);

  const setConversationRead = useCallback((readUpToId: number) => {
    setPartnerReadUpToId((prev) => (prev !== null ? Math.max(prev, readUpToId) : readUpToId));
  }, []);

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
    partnerReadUpToId,
    setConversationRead,
    lastMessageIdRef,
    fetchMissedMessages,
    messagesEndRef,
    loadMoreMessages,
    refreshUnread,
  };
}
