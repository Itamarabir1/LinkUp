import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import {
  getConversation,
  getMessages,
  sendMessage,
  type ConversationDetail,
  type MessageResponse,
} from '../api/client';
import { api, chatWsApi } from '../api/client';
import { CHAT_WS_URL } from '../config/env';
import { formatDateTimeNoSeconds } from '../utils/date';
import styles from './MessageThread.module.css';

const TYPING_THROTTLE_MS = 4000;
const TYPING_DISPLAY_TIMEOUT_MS = 5000;

export interface MessageThreadProps {
  /** כשמועבר — משמש במקום useParams (להטמעה בפנל). */
  conversationId?: string;
  /** true = פנל ימני: בלי כפתור חזרה, layout ממלא את המכל. */
  embedded?: boolean;
}

export default function MessageThread({ conversationId: propConversationId, embedded }: MessageThreadProps = {}) {
  const { conversationId: paramId } = useParams<{ conversationId: string }>();
  const conversationId = propConversationId ?? paramId ?? '';
  const { user } = useAuth();
  const { refreshUnread } = useChat();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [messagesNextCursor, setMessagesNextCursor] = useState<string | null>(null);
  const [messagesHasMore, setMessagesHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [input, setInput] = useState('');
  const [partnerTyping, setPartnerTyping] = useState(false);
  const [partnerTypingName, setPartnerTypingName] = useState<string | null>(null);
  const [partnerPresence, setPartnerPresence] = useState<{
    online: boolean;
    last_seen: string | null;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const lastTypingSentRef = useRef<number>(0);
  const typingHideTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const partnerIdRef = useRef<string | undefined>(undefined);

  const cid = conversationId;
  const partnerId = conversation?.partner?.user_id;

  useEffect(() => {
    partnerIdRef.current = partnerId;
  }, [partnerId]);

  function formatLastSeen(isoString: string): string {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'לפני כמה שניות';
    if (diffMins < 60) return `לפני ${diffMins} דקות`;
    if (diffMins < 1440) return `לפני ${Math.floor(diffMins / 60)} שעות`;
    return `לפני ${Math.floor(diffMins / 1440)} ימים`;
  }

  const fetchConversation = useCallback(async () => {
    if (!cid || !user?.user_id) return;
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
    } catch {
      setError('לא ניתן לטעון את השיחה');
    } finally {
      setLoading(false);
    }
  }, [cid, user?.user_id]);

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
    } catch {
      setError('לא ניתן לטעון הודעות ישנות');
    } finally {
      setLoadingMore(false);
    }
  }, [cid, messagesNextCursor, loadingMore]);

  useEffect(() => {
    fetchConversation();
  }, [fetchConversation]);

  // Keepalive ping to refresh presence TTL in chat-ws.
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
    void api
      .post(`/chat/conversations/${cid}/read`)
      .then(() => refreshUnread())
      .catch(() => {});
  }, [cid, refreshUnread]);

  // Poll partner presence every 30s.
  useEffect(() => {
    if (!partnerId) return;
    let cancelled = false;
    const fetchPresence = async () => {
      try {
        const { data } = await chatWsApi.get<{ online: boolean; last_seen: string | null }>(
          `/presence/${partnerId}`
        );
        if (!cancelled) setPartnerPresence(data);
      } catch {
        // ignore
      }
    };
    void fetchPresence();
    const interval = setInterval(fetchPresence, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [partnerId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket: connect when we have conversation id and token; handle incoming messages and typing.
  useEffect(() => {
    if (!cid) return;
    const token = localStorage.getItem('linkup_access_token');
    if (!token) return;

    const url = `${CHAT_WS_URL}/ws?token=${encodeURIComponent(token)}`;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url.startsWith('ws') ? url : `ws://${url.replace(/^https?:\/\//, '')}`);
    } catch {
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
        if (data?.type === 'user_offline') {
          const uid = String(data.user_id ?? '');
          if (uid && uid === partnerIdRef.current) {
            setPartnerPresence((prev) => ({
              online: false,
              last_seen: prev?.last_seen ?? null,
            }));
          }
          continue;
        }
        if (data?.type === 'unread_count') {
          void refreshUnread();
          continue;
        }
        if (typeof data?.message_id === 'number' && data?.conversation_id === cid) {
          void api
            .post(`/chat/conversations/${cid}/read`)
            .then(() => refreshUnread())
            .catch(() => {});
        }
        if (data?.type === 'typing_start') {
          setPartnerTyping(true);
          setPartnerTypingName((data.full_name as string) || null);
          if (typingHideTimeoutRef.current) clearTimeout(typingHideTimeoutRef.current);
          typingHideTimeoutRef.current = setTimeout(() => {
            setPartnerTyping(false);
            setPartnerTypingName(null);
            typingHideTimeoutRef.current = null;
          }, TYPING_DISPLAY_TIMEOUT_MS);
          continue;
        }
        if (data?.type === 'typing_stop' && data?.conversation_id === cid) {
          setPartnerTyping(false);
          setPartnerTypingName(null);
          if (typingHideTimeoutRef.current) {
            clearTimeout(typingHideTimeoutRef.current);
            typingHideTimeoutRef.current = null;
          }
          continue;
        }
        if (typeof (data as unknown as MessageResponse).message_id === 'number') {
          const msg = data as unknown as MessageResponse;
          setMessages((prev) => [...prev, msg]);
          if (msg.sender_id !== user?.user_id) setPartnerTyping(false);
        }
      }
    };

    return () => {
      if (typingHideTimeoutRef.current) {
        clearTimeout(typingHideTimeoutRef.current);
        typingHideTimeoutRef.current = null;
      }
      ws.close();
      wsRef.current = null;
    };
  }, [cid, user?.user_id, refreshUnread]);

  const sendTypingIfNeeded = useCallback(() => {
    if (!conversation?.partner?.user_id || !cid || !user?.user_id) return;
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
          recipient_id: conversation.partner.user_id,
          full_name: user.full_name ?? undefined,
        })
      );
    } catch {
      // ignore
    }
  }, [cid, conversation?.partner?.user_id, user?.user_id, user?.full_name]);

  const sendTypingStop = useCallback(() => {
    if (!conversation?.partner?.user_id || !cid || !user?.user_id) return;
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    lastTypingSentRef.current = 0; // reset throttle so next typing can send immediately
    try {
      ws.send(
        JSON.stringify({
          type: 'typing_stop',
          conversation_id: cid,
          recipient_id: conversation.partner.user_id,
          full_name: user.full_name ?? undefined,
        })
      );
    } catch {
      // ignore
    }
  }, [cid, conversation?.partner?.user_id, user?.user_id, user?.full_name]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const body = input.trim();
    if (!body || !cid || sending) return;
    setSending(true);
    setError('');
    try {
      const { data } = await sendMessage(cid, body);
      setMessages((prev) => [...prev, data]);
      setInput('');
      sendTypingStop();
    } catch {
      setError('שליחת ההודעה נכשלה');
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className={embedded ? styles.embeddedWrap : styles.page}>
        <p className="page-loading">טוען שיחה...</p>
      </div>
    );
  }

  if (error && !conversation) {
    return (
      <div className={embedded ? styles.embeddedWrap : styles.page}>
        <p className={styles.pageError}>{error}</p>
        {!embedded && (
          <Link to="/messages" className={`${styles.btn} ${styles.btnOutline}`} style={{ marginTop: '1rem' }}>
            חזרה להודעות
          </Link>
        )}
      </div>
    );
  }

  const partnerName = conversation?.partner?.full_name || (cid ? `שיחה` : '');
  const partnerAvatarUrl = conversation?.partner?.avatar_url;
  const partnerStatusText = partnerTyping
    ? `${partnerTypingName || partnerName} מקליד...`
    : partnerPresence?.online
      ? 'מחובר'
      : partnerPresence?.last_seen
        ? `נראה לאחרונה ${formatLastSeen(partnerPresence.last_seen)}`
        : '';

  return (
    <div
      className={embedded ? styles.embeddedWrap : styles.page}
      style={{ display: 'flex', flexDirection: 'column', height: embedded ? '100%' : undefined }}
    >
      <div style={{ marginBottom: embedded ? '0.5rem' : '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
        {!embedded && (
          <Link to="/messages" className={`${styles.btn} ${styles.btnOutline}`} style={{ fontSize: '0.875rem' }}>
            ← הודעות
          </Link>
        )}
        {partnerAvatarUrl ? (
          <img
            src={partnerAvatarUrl}
            alt=""
            style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover' }}
          />
        ) : (
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: 'var(--surface, #e5e7eb)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1rem',
              fontWeight: 600,
            }}
          >
            {(partnerName || '?').charAt(0)}
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 className={styles.pageTitle} style={{ margin: 0 }}>
            {partnerName}
          </h1>
          <div
            className={`${styles.partnerStatus} ${
              partnerStatusText === 'מחובר' ? styles.partnerStatusOnline : ''
            }`}
          >
            {partnerStatusText}
          </div>
        </div>
      </div>
      {error && <p className={styles.pageError}>{error}</p>}
      <div
        className={embedded ? styles.embeddedMessages : undefined}
        style={{
          flex: 1,
          overflowY: 'auto',
          border: embedded ? undefined : '1px solid #e5e7eb',
          borderRadius: embedded ? 0 : 8,
          padding: '1rem',
          minHeight: embedded ? 0 : 200,
          maxHeight: embedded ? 'none' : 400,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        {messagesHasMore && (
          <button
            type="button"
            className={styles.btnOutline}
            onClick={loadMoreMessages}
            disabled={loadingMore}
            style={{ alignSelf: 'center', marginBottom: '0.5rem' }}
          >
            {loadingMore ? 'טוען...' : 'טען הודעות ישנות יותר'}
          </button>
        )}
        {messages.length === 0 ? (
          <p className={styles.emptyText} style={{ margin: 'auto' }}>
            אין הודעות. שלח הודעה ראשונה.
          </p>
        ) : (
          messages.map((m) => {
            const isMe = m.sender_id === user?.user_id;
            return (
              <div
                key={m.message_id}
                style={{
                  alignSelf: isMe ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  padding: '0.5rem 0.75rem',
                  borderRadius: 8,
                  background: isMe ? 'var(--primary, #2563eb)' : 'var(--surface, #f3f4f6)',
                  color: isMe ? '#fff' : 'inherit',
                }}
              >
                <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{m.body}</div>
                <div
                  style={{
                    fontSize: '0.75rem',
                    opacity: 0.85,
                    marginTop: '0.25rem',
                  }}
                >
                  {formatDateTimeNoSeconds(m.created_at)}
                </div>
              </div>
            );
          })
        )}
        {partnerTyping && (
          <p className={styles.emptyText} style={{ margin: 0, fontSize: '0.875rem', opacity: 0.8 }}>
            {partnerTypingName ? `${partnerTypingName} מקליד...` : 'מקליד...'}
          </p>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSend} style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          value={input}
          onBlur={sendTypingStop}
          onChange={(e) => {
            setInput(e.target.value);
            sendTypingIfNeeded();
          }}
          placeholder="כתוב הודעה..."
          className={styles.formInput}
          style={{ flex: 1 }}
          maxLength={10000}
        />
        <button type="submit" className={`${styles.btn} ${styles.btnSuccess}`} disabled={sending || !input.trim()}>
          {sending ? '...' : 'שלח'}
        </button>
      </form>
    </div>
  );
}
