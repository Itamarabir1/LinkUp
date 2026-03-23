import { Link } from 'react-router-dom';
import ErrorBanner from '../../components/ErrorBanner';
import { formatDateTimeNoSeconds } from '../../utils/date';
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
          <Link to="/messages" className={`${styles.btn} ${styles.btnOutline} ${styles.backLinkSpaced}`}>
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
        ? `נראה לאחרונה ${formatChatLastSeen(partnerPresence.last_seen)}`
        : '';

  const rootClass = embedded ? `${styles.embeddedWrap} ${styles.threadColumnFill}` : `${styles.page} ${styles.threadColumn}`;
  const headerClass = embedded ? styles.threadHeaderEmbedded : styles.threadHeader;

  return (
    <div className={rootClass}>
      <div className={headerClass}>
        {!embedded && (
          <Link to="/messages" className={`${styles.btn} ${styles.btnOutline} ${styles.backLinkSmall}`}>
            ← הודעות
          </Link>
        )}
        {partnerAvatarUrl ? (
          <img src={partnerAvatarUrl} alt="" className={styles.partnerAvatar} />
        ) : (
          <div className={styles.partnerAvatarPlaceholder}>{(partnerName || '?').charAt(0)}</div>
        )}
        <div className={styles.threadTitleWrap}>
          <h1 className={`${styles.pageTitle} ${styles.threadTitleTight}`}>{partnerName}</h1>
          <div
            className={`${styles.partnerStatus} ${
              partnerStatusText === 'מחובר' ? styles.partnerStatusOnline : ''
            }`}
          >
            {partnerStatusText}
          </div>
        </div>
      </div>
      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}
      <div className={embedded ? styles.messagesScrollerEmbedded : styles.messagesScroller}>
        {messagesHasMore && (
          <button
            type="button"
            className={`${styles.btnOutline} ${styles.loadOlderBtn}`}
            onClick={() => void loadMoreMessages()}
            disabled={loadingMore}
          >
            {loadingMore ? 'טוען...' : 'טען הודעות ישנות יותר'}
          </button>
        )}
        {messages.length === 0 ? (
          <p className={`${styles.emptyText} ${styles.emptyMessages}`}>אין הודעות. שלח הודעה ראשונה.</p>
        ) : (
          messages.map((m) => {
            const isMe = m.sender_id === user?.user_id;
            return (
              <div key={m.message_id} className={isMe ? styles.msgBubbleMe : styles.msgBubbleThem}>
                <div className={styles.msgBody}>{m.body}</div>
                <div className={styles.msgTime}>{formatDateTimeNoSeconds(m.created_at)}</div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSend} className={styles.composeRow}>
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="כתוב הודעה..."
          className={`${styles.formInput} ${styles.composeInputGrow}`}
          maxLength={10000}
        />
        <button type="submit" className={`${styles.btn} ${styles.btnSuccess}`} disabled={sending || !input.trim()}>
          {sending ? '...' : 'שלח'}
        </button>
      </form>
    </div>
  );
}
