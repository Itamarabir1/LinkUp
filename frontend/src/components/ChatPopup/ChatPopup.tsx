import { MapPin, Maximize2, X, Send } from 'lucide-react';
import ChatErrorBoundary from '../ChatErrorBoundary/ChatErrorBoundary';
import { formatDateTimeNoSeconds } from '../../utils/date';
import { useChatPopup } from './useChatPopup';
import styles from './ChatPopup.module.css';

interface ChatPopupProps {
  conversationId: string;
}

function ChatPopupContent({ conversationId }: ChatPopupProps) {
  const {
    user,
    closeChat,
    conversation,
    messages,
    loading,
    sending,
    fetchError,
    sendError,
    input,
    setInput,
    messagesEndRef,
    listRef,
    handleSend,
    onKeyDown,
    handleMaximize,
  } = useChatPopup(conversationId);

  if (loading) {
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

  if (!conversation) {
    return (
      <div className={styles.popup}>
        <div className={styles.header}>
          <div className={styles.headerPlaceholder} role="alert">
            {fetchError || 'לא ניתן לטעון את השיחה'}
          </div>
        </div>
        <div className={styles.messagesArea} />
        <div className={styles.sendArea} />
      </div>
    );
  }

  const partnerName = conversation.partner?.full_name || 'שיחה';
  const partnerAvatar = conversation.partner?.avatar_url;
  const routeLabel = conversation.route_label?.trim() || null;

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
        {sendError ? (
          <p className={styles.sendError} role="alert">
            {sendError}
          </p>
        ) : null}
        <div className={styles.sendRow}>
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
        </div>
      </form>
    </div>
  );
}

export default function ChatPopup(props: ChatPopupProps) {
  return (
    <ChatErrorBoundary>
      <ChatPopupContent {...props} />
    </ChatErrorBoundary>
  );
}
