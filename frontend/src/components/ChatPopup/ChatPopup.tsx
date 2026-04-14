import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { MapPin, Maximize2, X, Send } from 'lucide-react';
import { formatDayMonthLong, formatTimeHm } from '../../utils/date';
import ChatErrorBoundary from '../ChatErrorBoundary/ChatErrorBoundary';
import { useChatPopup } from './useChatPopup';
import styles from './ChatPopup.module.css';

interface ChatPopupProps {
  conversationId: string;
}

function ChatPopupContent({ conversationId }: ChatPopupProps) {
  const { t } = useTranslation('common');
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
          <div className={styles.headerPlaceholder}>{t('chat_popup_loading')}</div>
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
            {fetchError || t('err_load_conversation')}
          </div>
        </div>
        <div className={styles.messagesArea} />
        <div className={styles.sendArea} />
      </div>
    );
  }

  const partnerName = conversation.partner?.full_name || t('chat_popup_conversation_fallback');
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
            aria-label={t('chat_popup_maximize')}
          >
            <Maximize2 size={16} />
          </button>
          <button
            type="button"
            className={styles.iconBtn}
            onClick={closeChat}
            aria-label={t('chat_popup_close')}
          >
            <X size={16} />
          </button>
        </div>
      </header>

      <div ref={listRef} className={styles.messagesArea}>
        {messages.length === 0 ? (
          <p className={styles.emptyMsg}>{t('chat_popup_empty')}</p>
        ) : (
          messages.reduce<ReactNode[]>((acc, m, i) => {
            const isMe = m.sender_id === user?.user_id;
            const msgDate = new Date(m.created_at).toDateString();
            const prevDate = i > 0 ? new Date(messages[i - 1].created_at).toDateString() : null;
            if (msgDate !== prevDate) {
              const label = formatDayMonthLong(m.created_at);
              acc.push(
                <div key={`day-${msgDate}-${i}`} className={styles.dayDivider}>
                  <div className={styles.dayLine} aria-hidden />
                  <span className={styles.dayLabel}>{label}</span>
                  <div className={styles.dayLine} aria-hidden />
                </div>
              );
            }
            acc.push(
              <div key={m.message_id} className={isMe ? styles.bubbleOut : styles.bubbleIn}>
                <div className={styles.bubbleText}>{m.body}</div>
                <div className={styles.bubbleTime}>{formatTimeHm(m.created_at)}</div>
              </div>
            );
            return acc;
          }, [])
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
            placeholder={t('msg_compose_placeholder')}
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
            aria-label={t('msg_send')}
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
