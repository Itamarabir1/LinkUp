import { useCallback, useEffect, useState } from 'react';
import { MessageCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import { listConversations } from '../api/chat';
import type { ConversationListItem } from '../types/api';
import { formatConversationTime } from '../utils/date';
import ErrorBanner from '../components/ErrorBanner';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import MessageThread from './MessageThread';
import styles from './Messages.module.css';

export default function Messages() {
  const { user } = useAuth();
  const { openChat, panelConversationId, unreadMessages } = useChat();
  const [list, setList] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchList = useCallback(async () => {
    if (!user?.user_id) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await listConversations();
      const sorted = (Array.isArray(data) ? data : []).slice().sort((a, b) => {
        const at = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const bt = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return bt - at;
      });
      setList(sorted);
    } catch (err) {
      setError(getApiErrorMessage(err, apiErr('err_load_conversations')));
    } finally {
      setLoading(false);
    }
  }, [user?.user_id]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  return (
    <div className={styles.container}>
      <aside className={styles.sidebar}>
        <header className={styles.sidebarHeader}>
          {unreadMessages > 0 && (
            <span className={styles.newCount}>{unreadMessages} חדשות</span>
          )}
        </header>

        {loading ? (
          <div className={styles.loading}>טוען...</div>
        ) : error ? (
          <ErrorBanner message={error} variant="compact" className={styles.error} />
        ) : list.length === 0 ? (
          <div className={styles.emptyList}>
            <MessageCircle size={44} strokeWidth={1.5} className={styles.emptyIcon} />
            <p className={styles.emptyTitle}>אין הודעות עדיין</p>
            <p className={styles.emptySub}>הודעות יישלחו דרך נסיעות</p>
          </div>
        ) : (
          <div className={styles.conversationList}>
            {list.map((c) => (
              <button
                key={c.conversation_id}
                type="button"
                className={`${styles.conversationRow} ${
                  panelConversationId === c.conversation_id ? styles.active : ''
                } ${c.has_unread ? styles.convUnread : ''}`}
                onClick={() => openChat(c.conversation_id)}
              >
                <div className={styles.avatarWrap}>
                  {c.partner.avatar_url ? (
                    <img src={c.partner.avatar_url} alt="" className={styles.avatar} />
                  ) : (
                    <span className={styles.avatarLetter}>
                      {(c.partner.full_name || '?').charAt(0).toUpperCase()}
                    </span>
                  )}
                  {c.has_unread && <span className={styles.unreadDot} aria-hidden />}
                </div>
                <div className={styles.rowContent}>
                  <div className={styles.rowFirst}>
                    <span className={`${styles.partnerName} ${c.has_unread ? styles.convName : ''}`}>
                      {c.partner.full_name || `משתמש #${c.partner.user_id}`}
                    </span>
                    <span className={styles.rowTime}>
                      {formatConversationTime(c.last_message_at)}
                    </span>
                  </div>
                  {c.last_message_preview && (
                    <p className={styles.lastPreview}>{c.last_message_preview}</p>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </aside>

      <section className={styles.panel}>
        {panelConversationId ? (
          <MessageThread conversationId={panelConversationId} embedded />
        ) : (
          <div className={styles.panelPlaceholder}>
            <MessageCircle size={52} strokeWidth={1.5} className={styles.placeholderIcon} />
            <p className={styles.placeholderText}>בחר שיחה כדי להתחיל</p>
          </div>
        )}
      </section>
    </div>
  );
}
