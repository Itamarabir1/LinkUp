import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Maximize2, X, Send } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import {
  getConversation,
  getMessages,
  sendMessage,
  type ConversationDetail,
  type MessageResponse,
} from '../../api/client';
import { formatDateTimeNoSeconds } from '../../utils/date';
import styles from './ChatPopup.module.css';

interface ChatPopupProps {
  conversationId: string;
}

export default function ChatPopup({ conversationId }: ChatPopupProps) {
  const { user } = useAuth();
  const { closeChat } = useChat();
  const navigate = useNavigate();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const fetchData = useCallback(async () => {
    if (!conversationId || !user?.user_id) return;
    setLoading(true);
    try {
      const [convRes, msgRes] = await Promise.all([
        getConversation(conversationId),
        getMessages(conversationId, { limit: 30 }),
      ]);
      setConversation(convRes.data);
      setMessages(msgRes.data?.items ?? []);
    } catch {
      setConversation(null);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [conversationId, user?.user_id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const body = input.trim();
      if (!body || !conversationId || sending) return;
      setSending(true);
      setInput('');
      try {
        const { data } = await sendMessage(conversationId, body);
        setMessages((prev) => [...prev, data]);
      } catch {
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
      handleSend(e as unknown as React.FormEvent);
    }
  };

  const handleMaximize = () => {
    navigate(`/messages/${conversationId}`);
    closeChat();
  };

  const partnerName = conversation?.partner?.full_name || 'שיחה';
  const partnerAvatar = conversation?.partner?.avatar_url;
  const routeLabel = null; // TODO: when conversation has route info

  if (loading || !conversation) {
    return (
      <div className={styles.popup}>
        <div className={styles.header}>
          <div className={styles.headerPlaceholder}>טוען...</div>
        </div>
        <div className={styles.messagesArea} />
        <div className={styles.sendArea} />
      </div>
    );
  }

  return (
    <div className={styles.popup}>
      <header className={styles.header}>
        <div className={styles.avatarWrap}>
          {partnerAvatar ? (
            <img src={partnerAvatar} alt="" className={styles.avatar} />
          ) : (
            <span className={styles.avatarLetter}>{partnerName.charAt(0).toUpperCase()}</span>
          )}
        </div>
        <div className={styles.headerInfo}>
          <span className={styles.partnerName}>{partnerName}</span>
          {routeLabel && (
            <span className={styles.routeLabel}>
              <MapPin size={10} />
              {routeLabel}
            </span>
          )}
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.iconBtn}
            onClick={handleMaximize}
            aria-label="הגדל"
          >
            <Maximize2 size={16} />
          </button>
          <button
            type="button"
            className={styles.iconBtn}
            onClick={closeChat}
            aria-label="סגור"
          >
            <X size={16} />
          </button>
        </div>
      </header>

      <div ref={listRef} className={styles.messagesArea}>
        {messages.length === 0 ? (
          <p className={styles.emptyMsg}>אין הודעות. שלח הודעה ראשונה.</p>
        ) : (
          messages.map((m) => {
            const isMe = m.sender_id === user?.user_id;
            return (
              <div
                key={m.message_id}
                className={isMe ? styles.bubbleOut : styles.bubbleIn}
              >
                <div className={styles.bubbleText}>{m.body}</div>
                <div className={styles.bubbleTime}>
                  {formatDateTimeNoSeconds(m.created_at)}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className={styles.sendArea} onSubmit={handleSend}>
        <textarea
          className={styles.textarea}
          placeholder="כתוב הודעה..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          maxLength={10000}
        />
        <button
          type="submit"
          className={styles.sendBtn}
          disabled={sending || !input.trim()}
          aria-label="שלח"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
