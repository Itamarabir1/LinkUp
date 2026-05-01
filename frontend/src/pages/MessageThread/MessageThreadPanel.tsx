import type { FormEvent, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Loader2, Send } from 'lucide-react';
import ErrorBanner from '../../components/ErrorBanner';
import { formatDateFull, formatTimeHm } from '../../utils/date';
import { formatChatLastSeen } from './messageThread.utils';
import type { ChatListRow } from '../../types/chatList';
import type { MessageThreadViewModel } from './useMessageThread';
import styles from './MessageThread.module.css';

function rowCreatedAt(row: ChatListRow): string {
  return row.kind === 'confirmed' ? row.message.created_at : row.created_at;
}

function rowSenderId(row: ChatListRow): string {
  return row.kind === 'confirmed' ? row.message.sender_id : row.sender_id;
}

function rowBody(row: ChatListRow): string {
  return row.kind === 'confirmed' ? row.message.body : row.body;
}

export interface MessageThreadPanelProps {
  vm: MessageThreadViewModel;
  embedded?: boolean;
}

export default function MessageThreadPanel({ vm, embedded }: MessageThreadPanelProps) {
  const { t } = useTranslation('common');
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
    partnerReadUpToId,
    messagesEndRef,
    loadMoreMessages,
    handleSend,
    onInputChange,
  } = vm;

  if (loading) {
    return (
      <div className={embedded ? styles.embeddedWrap : styles.page}>
        <p className={styles.pageLoading}>{t('msg_thread_loading')}</p>
      </div>
    );
  }

  if (error && !conversation) {
    return (
      <div className={embedded ? styles.embeddedWrap : styles.page}>
        <ErrorBanner message={error} className={styles.pageError} />
        {!embedded && (
          <Link to="/messages" className={styles.backBtn} style={{ margin: '16px' }}>
            {t('msg_back_to_messages')}
          </Link>
        )}
      </div>
    );
  }

  const partnerName = conversation?.partner?.full_name || (cid ? t('msg_conversation_fallback') : '');
  const partnerAvatarUrl = conversation?.partner?.avatar_url;

  const partnerStatusText = partnerTyping
    ? t('msg_typing', { name: partnerTypingName || partnerName })
    : partnerPresence?.online
      ? t('msg_online')
      : partnerPresence?.last_seen
        ? t('msg_last_seen', { when: formatChatLastSeen(partnerPresence.last_seen) })
        : '';

  const isOnline = !partnerTyping && partnerPresence?.online;

  const headerClass = embedded ? styles.threadHeaderEmbedded : styles.threadHeader;
  const scrollerClass = embedded ? styles.messagesScrollerEmbedded : styles.messagesScroller;

  return (
    <div className={embedded ? styles.embeddedWrap : styles.page}>
      <div className={headerClass}>
        {!embedded && (
          <Link to="/messages" className={styles.backBtn} aria-label={t('msg_back_aria')}>
            <ArrowRight size={16} />
          </Link>
        )}

        {partnerAvatarUrl ? (
          <img src={partnerAvatarUrl} alt="" className={styles.partnerAvatar} loading="eager" />
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
            {loadingMore ? t('loading') : t('msg_load_older')}
          </button>
        ) : null}

        {messages.length === 0 ? (
          <p className={styles.emptyMessages}>{t('msg_empty_thread')}</p>
        ) : (
          messages.reduce<ReactNode[]>((acc, row, i) => {
            const createdAt = rowCreatedAt(row);
            const isMe = rowSenderId(row) === user?.user_id;
            const isPending = row.kind === 'pending';
            const msgIsRead =
              row.kind === 'confirmed' &&
              partnerReadUpToId !== null &&
              row.message.message_id <= partnerReadUpToId;
            const msgDay = new Date(createdAt).toDateString();
            const prevDay =
              i > 0 ? new Date(rowCreatedAt(messages[i - 1])).toDateString() : null;

            if (msgDay !== prevDay) {
              acc.push(
                <div key={`day-${msgDay}-${i}`} className={styles.dayDivider}>
                  <div className={styles.dayLine} aria-hidden />
                  <span className={styles.dayLabel}>{formatDateFull(createdAt)}</span>
                  <div className={styles.dayLine} aria-hidden />
                </div>
              );
            }

            const bubbleKey =
              row.kind === 'confirmed' ? row.message.message_id : `pending-${row.client_message_id}`;
            const bubbleClass = [
              isMe ? styles.msgBubbleMe : styles.msgBubbleThem,
              isPending ? styles.msgPending : '',
            ]
              .filter(Boolean)
              .join(' ');

            acc.push(
              <div
                key={bubbleKey}
                className={bubbleClass}
                aria-busy={isPending ? true : undefined}
              >
                <div className={styles.msgBody}>
                  <div className={styles.msgText}>{rowBody(row)}</div>
                  <div className={styles.msgTime}>
                    {formatTimeHm(createdAt)}
                    {isMe && isPending ? (
                      <Loader2
                        className={styles.msgPendingSpinner}
                        size={12}
                        aria-hidden
                        strokeWidth={2.5}
                      />
                    ) : null}
                    {isMe && !isPending ? (
                      <span
                        className={styles.readReceipt}
                        aria-label={msgIsRead ? t('msg_read') : t('msg_sent')}
                        aria-live="polite"
                      >
                        <svg
                          width="16"
                          height="10"
                          viewBox="0 0 16 10"
                          fill="none"
                          className={msgIsRead ? styles.readReceiptRead : styles.readReceiptSent}
                        >
                          <polyline
                            points="1,6 4,9 9,2"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                          <polyline
                            points="5,6 8,9 13,2"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                    ) : null}
                  </div>
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
          aria-label={t('msg_send')}
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
          placeholder={t('msg_compose_placeholder')}
          className={styles.composeTextarea}
          rows={1}
          maxLength={10000}
        />
      </form>
    </div>
  );
}
