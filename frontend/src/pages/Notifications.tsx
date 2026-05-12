import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  UserPlus,
  UserMinus,
  Users,
  UserCheck,
  Bell,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useChat, getNotificationItemKey } from '../context/ChatContext';
import { fetchMyNotifications } from '../api/users';
import { qk } from '../api/queryKeys';
import type { NotificationItem } from '../types/api';
import { formatMonthYearLong, formatRelativeNotificationTime, formatWeekdayLong } from '../utils/date';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { NOTIFICATIONS_REFRESH_EVENT } from '../config/constants';
import RouteArrow from '../components/RouteArrow/RouteArrow';
import { usePageTitle } from '../hooks/usePageTitle';
import styles from './Notifications.module.css';

type DisplayType = 'booking_approved' | 'booking_rejected' | 'ride_cancelled' | 'booking_request' | 'booking_cancelled_by_passenger' | 'group_joined' | 'group_member_joined' | 'pending_approval' | 'default';

/** Maps backend type to display type (icon + style). */
function getDisplayType(type: string): DisplayType {
  if (type === 'booking_confirmed') return 'booking_approved';
  if (type === 'ride_request') return 'booking_request';
  if (type === 'pending_approval') return 'pending_approval';
  const known: DisplayType[] = ['booking_approved', 'booking_rejected', 'ride_cancelled', 'booking_request', 'booking_cancelled_by_passenger', 'group_joined', 'group_member_joined', 'pending_approval'];
  return known.includes(type as DisplayType) ? (type as DisplayType) : 'default';
}

export default function Notifications() {
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const { t } = useTranslation(['common', 'nav']);
  const pageTitle = t('nav:notifications');
  usePageTitle(pageTitle);
  const { user } = useAuth();
  const {
    markNotificationRead,
    markAllNotificationsRead,
    refreshUnreadNotifications,
    isNotificationRead,
    unreadNotifications,
  } = useChat();
  const queryClient = useQueryClient();
  const {
    data,
    isLoading: loading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    error: fetchError,
  } = useInfiniteQuery({
    queryKey: qk.notifications.page(20),
    queryFn: async ({ pageParam }) => {
      const { data } = await fetchMyNotifications({ limit: 20, after: pageParam ?? undefined });
      return data;
    },
    enabled: !!user?.user_id,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 30_000,
  });
  const list = useMemo(
    () => data?.pages.flatMap((page) => page.items) ?? [],
    [data?.pages]
  );
  const error = fetchError ? getApiErrorMessage(fetchError, apiErr('err_load_notifications')) : '';

  const getTimeGroup = useCallback(
    (dateStr: string): string => {
      const d = new Date(dateStr);
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      const diffDays = Math.round(
        (today.getTime() - dayStart.getTime()) / (24 * 60 * 60 * 1000)
      );
      if (diffDays === 0) return t('today');
      if (diffDays === 1) return t('yesterday');
      if (diffDays >= 2 && diffDays < 7) return formatWeekdayLong(d);
      return formatMonthYearLong(d);
    },
    [t]
  );

  useEffect(() => {
    if (!user?.user_id) return;
    void refreshUnreadNotifications();
  }, [user?.user_id, list, refreshUnreadNotifications]);

  useEffect(() => {
    const onRefresh = () => {
      void queryClient.invalidateQueries({ queryKey: qk.notifications.page(20) });
    };
    window.addEventListener(NOTIFICATIONS_REFRESH_EVENT, onRefresh);
    return () => window.removeEventListener(NOTIFICATIONS_REFRESH_EVENT, onRefresh);
  }, [queryClient]);

  const groupedList = useMemo(() => {
    const groups: Record<string, { label: string; date: Date; items: NotificationItem[] }> = {};

    for (const n of list) {
      const label = getTimeGroup(n.created_at);
      if (!groups[label]) {
        groups[label] = {
          label,
          date: new Date(n.created_at),
          items: [],
        };
      }
      groups[label].items.push(n);
    }

    return Object.values(groups).sort((a, b) => b.date.getTime() - a.date.getTime());
  }, [list, getTimeGroup]);

  const getNotificationTarget = (type: string): string | null => {
    switch (type) {
      case 'ride_request':
      case 'pending_approval':
      case 'booking_cancelled_by_passenger':
        return '/my-bookings?tab=driver';
      case 'booking_confirmed':
      case 'booking_approved':
      case 'booking_rejected':
      case 'ride_cancelled':
        return '/my-bookings';
      case 'group_joined':
      case 'group_member_joined':
        return '/groups';
      default:
        return null;
    }
  };

  const handleRowClick = useCallback(
    (n: NotificationItem) => {
      if (!isNotificationRead(n)) markNotificationRead(n);
      const target = getNotificationTarget(n.type);
      if (target) navigateRef.current(target);
    },
    [isNotificationRead, markNotificationRead]
  );

  function getAvatarColorClass(displayType: DisplayType): string {
    if (displayType === 'booking_approved') return styles.avatarApproved;
    if (displayType === 'booking_rejected') return styles.avatarRejected;
    if (displayType === 'ride_cancelled') return styles.avatarCancelled;
    if (displayType === 'booking_request' || displayType === 'pending_approval') return styles.avatarRequest;
    if (displayType === 'group_joined' || displayType === 'group_member_joined') return styles.avatarGroup;
    return styles.avatarDefault;
  }

  function getBadgeColorClass(displayType: DisplayType): string {
    if (
      displayType === 'booking_approved' ||
      displayType === 'group_joined' ||
      displayType === 'group_member_joined'
    )
      return styles.badgeGreen;
    if (displayType === 'booking_rejected' || displayType === 'booking_cancelled_by_passenger')
      return styles.badgeRed;
    if (displayType === 'ride_cancelled') return styles.badgeAmber;
    return styles.badgeBlue;
  }

  function getAvatarLetter(n: NotificationItem): string {
    return (n.other_party_name || '?').charAt(0).toUpperCase();
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <p className={styles.pageLoading}>{t('loading')}</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className="sr-only">{pageTitle}</h1>
      {error && <p className={styles.pageError}>{error}</p>}

      {list.length === 0 ? (
        <div className={styles.empty}>
          <Bell size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <p className={styles.emptyTitle}>{t('notif_empty_title')}</p>
          <p className={styles.emptySub}>{t('notif_empty_sub')}</p>
        </div>
      ) : (
        <div className={styles.groups}>
          {unreadNotifications > 0 && (
            <div className={styles.markAllWrap}>
              <button
                type="button"
                className={styles.markAllRead}
                onClick={() => markAllNotificationsRead()}
              >
                {t('notif_mark_all_read')}
              </button>
            </div>
          )}
          {groupedList.map(({ label, items }) => (
            <div key={label} className={styles.group}>
              <h2 className={styles.groupTitle}>{label}</h2>
              {items.map((n) => {
                const key = getNotificationItemKey(n);
                const read = n.is_read;
                const displayType = getDisplayType(n.type);
                const origin = n.ride_origin?.trim() || '';
                const dest = n.ride_destination?.trim() || '';
                const hasRoute = Boolean(origin || dest);
                const hasFullRoute = Boolean(origin && dest);
                return (
                  <button
                    key={key}
                    type="button"
                    className={`${styles.notificationRow} ${read ? '' : styles.unread}`}
                    onClick={() => handleRowClick(n)}
                  >
                    <div className={styles.avatarWrap}>
                      <div className={`${styles.avatarCircle} ${getAvatarColorClass(displayType)}`}>
                        {getAvatarLetter(n)}
                      </div>
                      <div className={`${styles.typeBadge} ${getBadgeColorClass(displayType)}`}>
                        {displayType === 'booking_approved' && (
                          <CheckCircle size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {displayType === 'booking_rejected' && (
                          <XCircle size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {displayType === 'ride_cancelled' && (
                          <AlertTriangle size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {displayType === 'booking_request' && (
                          <UserPlus size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {displayType === 'booking_cancelled_by_passenger' && (
                          <UserMinus size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {displayType === 'group_joined' && (
                          <Users size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {displayType === 'group_member_joined' && (
                          <UserCheck size={10} strokeWidth={2.5} color="#fff" />
                        )}
                        {(displayType === 'pending_approval' || displayType === 'default') && (
                          <Bell size={10} strokeWidth={2.5} color="#fff" />
                        )}
                      </div>
                    </div>

                    <div className={styles.notifContent}>
                      <p className={read ? styles.notifTitle : `${styles.notifTitle} ${styles.notifTitleUnread}`}>
                        {n.title}
                      </p>
                      {(n.body || hasRoute) && (
                        <p className={styles.notifBody}>
                          {n.body}
                          {n.body && hasRoute ? ' · ' : null}
                          {hasFullRoute ? (
                            <>
                              {origin}
                              <RouteArrow />
                              {dest}
                            </>
                          ) : hasRoute ? (
                            <>{origin || dest}</>
                          ) : null}
                        </p>
                      )}
                      <p
                        className={
                          read ? styles.notifTime : `${styles.notifTime} ${styles.notifTimeUnread}`
                        }
                      >
                        {formatRelativeNotificationTime(n.created_at)}
                      </p>
                    </div>

                    {!read && <span className={styles.unreadDot} aria-hidden />}
                  </button>
                );
              })}
            </div>
          ))}
          {hasNextPage && (
            <div className={styles.loadMoreWrap}>
              <button
                type="button"
                className={styles.loadMoreBtn}
                onClick={() => void fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? t('loading') : t('common:load_more', { defaultValue: 'טען עוד' })}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
