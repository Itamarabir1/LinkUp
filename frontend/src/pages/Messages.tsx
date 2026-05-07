import { useEffect, useRef } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { MessageCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import { inboxPageSizeDefault, listConversations } from '../api/chat';
import { qk } from '../api/queryKeys';
import { formatConversationTime } from '../utils/date';
import ErrorBanner from '../components/ErrorBanner';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { usePageTitle } from '../hooks/usePageTitle';
import MessageThread from './MessageThread';
import styles from './Messages.module.css';

const inboxLimit = inboxPageSizeDefault;

export default function Messages() {
  const { t } = useTranslation('nav');
  const pageTitle = t('messages');
  usePageTitle(pageTitle);
  const { user } = useAuth();
  const { openChat, panelConversationId, unreadMessages } = useChat();

  const sidebarRef = useRef<HTMLElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const {
    data,
    isLoading: loading,
    error: fetchError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: qk.chat.conversations(inboxLimit),
    queryFn: ({ pageParam }) => listConversations({ limit: inboxLimit, after: pageParam }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: !!user?.user_id,
    staleTime: 30_000,
    refetchOnReconnect: false,
  });

  const list = data?.pages.flatMap((p) => p.items) ?? [];

  useEffect(() => {
    const root = sidebarRef.current;
    const target = sentinelRef.current;
    if (!root || !target || !hasNextPage) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const hit = entries[0]?.isIntersecting;
        if (hit && hasNextPage && !isFetchingNextPage) {
          void fetchNextPage();
        }
      },
      { root, rootMargin: '100px' },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, list.length]);

  const error = fetchError ? getApiErrorMessage(fetchError, apiErr('err_load_conversations')) : '';

  return (
    <div className={styles.container}>
      <h1 className="sr-only">{pageTitle}</h1>
      <aside ref={sidebarRef} className={styles.sidebar}>
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
                    <img src={c.partner.avatar_url} alt="" className={styles.avatar} loading="lazy" />
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
            <div ref={sentinelRef} className={styles.inboxSentinel} aria-hidden />
            {isFetchingNextPage && (
              <div className={styles.loadingMore}>טוען עוד…</div>
            )}
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
