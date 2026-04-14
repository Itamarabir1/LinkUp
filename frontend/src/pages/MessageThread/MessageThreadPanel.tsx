import type { FormEvent, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Send } from 'lucide-react';
import ErrorBanner from '../../components/ErrorBanner';
import { formatChatLastSeen } from './messageThread.utils';
import type { MessageThreadViewModel } from './useMessageThread';
import styles from './MessageThread.module.css';

export interface MessageThreadPanelProps {
  vm: MessageThreadViewModel;
  embedded?: boolean;
}

export default function MessageThreadPanel({ vm, embedded }: MessageThreadPanelProps) {
  const {
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
  } = vm;

  function formatBubbleTime(dateStr: string): string {
    const d = new Date(dateStr);
    return d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
  }

  function getDayLabel(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('he-IL', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  }

  if (loading) {
    return (
      <div className={embedded ? styles.embeddedWrap : styles.page}>
        <p className={styles.pageLoading}>טוען שיחה...</p>
      </div>
    );
  }

  if (error && !conversation) {
    return (
      <div className={embedded ? styles.embeddedWrap : styles.page}>
        <ErrorBanner message={error} className={styles.pageError} />
        {!embedded && (
          <Link to="/messages" className={styles.backBtn} style={{ margin: '16px' }}>
            חזרה להודעות
          </Link>
        )}
      </div>
    );
  }

  const partnerName = conversation?.partner?.full_name || (cid ? 'שיחה' : '');
  const partnerAvatarUrl = conversation?.partner?.avatar_url;

  const partnerStatusText = partnerTyping
    ? `${partnerTypingName || partnerName} מקליד...`
    : partnerPresence?.online
      ? 'מחובר'
      : partnerPresence?.last_seen
        ? `נראה לאחרונה ${formatChatLastSeen(partnerPresence.last_seen)}`
        : '';

  const isOnline = !partnerTyping && partnerPresence?.online;

  const headerClass = embedded ? styles.threadHeaderEmbedded : styles.threadHeader;
  const scrollerClass = embedded ? styles.messagesScrollerEmbedded : styles.messagesScroller;

  return (
    <div className={embedded ? styles.embeddedWrap : styles.page}>
      <div className={headerClass}>
        {!embedded && (
          <Link to="/messages" className={styles.backBtn} aria-label="חזרה">
            <ArrowRight size={16} />
          </Link>
        )}

        {partnerAvatarUrl ? (
          <img src={partnerAvatarUrl} alt="" className={styles.partnerAvatar} />
        ) : (
          <div className={styles.partnerAvatarPlaceholder}>
            {(partnerName || '?').charAt(0).toUpperCase()}
          </div>
        )}

        <div className={styles.threadTitleWrap}>
          <h1 className={styles.threadTitleTight}>{partnerName}</h1>
          {partnerStatusText ? (
            <div className={styles.partnerStatus}>
              {isOnline ? <span className={styles.onlineDot} /> : null}
              {partnerStatusText}
            </div>
          ) : null}
        </div>
      </div>

      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

      <div className={scrollerClass}>
        {messagesHasMore ? (
          <button
            type="button"
            className={styles.loadOlderBtn}
            onClick={() => void loadMoreMessages()}
            disabled={loadingMore}
          >
            {loadingMore ? 'טוען...' : 'טען הודעות ישנות יותר'}
          </button>
        ) : null}

        {messages.length === 0 ? (
          <p className={styles.emptyMessages}>אין הודעות. שלח הודעה ראשונה.</p>
        ) : (
          messages.reduce<ReactNode[]>((acc, m, i) => {
            const isMe = m.sender_id === user?.user_id;
            const msgDay = new Date(m.created_at).toDateString();
            const prevDay = i > 0 ? new Date(messages[i - 1].created_at).toDateString() : null;

            if (msgDay !== prevDay) {
              acc.push(
                <div key={`day-${msgDay}-${i}`} className={styles.dayDivider}>
                  <div className={styles.dayLine} aria-hidden />
                  <span className={styles.dayLabel}>{getDayLabel(m.created_at)}</span>
                  <div className={styles.dayLine} aria-hidden />
                </div>
              );
            }

            acc.push(
              <div key={m.message_id} className={isMe ? styles.msgBubbleMe : styles.msgBubbleThem}>
                <div className={styles.msgBody}>
                  <div className={styles.msgText}>{m.body}</div>
                  <div className={styles.msgTime}>{formatBubbleTime(m.created_at)}</div>
                </div>
              </div>
            );

            return acc;
          }, [])
        )}

        {partnerTyping ? (
          <div className={styles.typingBubble}>
            <div className={styles.typingDot} />
            <div className={styles.typingDot} />
            <div className={styles.typingDot} />
          </div>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className={styles.composeRow}>
        <button
          type="submit"
          className={styles.sendBtn}
          disabled={sending || !input.trim()}
          aria-label="שלח"
        >
          <Send size={16} strokeWidth={2} />
        </button>
        <textarea
          value={input}
          onChange={(e) => {
            onInputChange(e.target.value);
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 100)}px`;
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void handleSend(e as unknown as FormEvent<HTMLFormElement>);
            }
          }}
          placeholder="כתוב הודעה..."
          className={styles.composeTextarea}
          rows={1}
          maxLength={10000}
        />
      </form>
    </div>
  );
}
