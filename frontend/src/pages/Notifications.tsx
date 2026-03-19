import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { api } from '../api/client';
import type { NotificationItem } from '../types/api';
import { formatDateTimeNoSeconds } from '../utils/date';
import styles from './Notifications.module.css';

type DisplayType = 'booking_approved' | 'booking_rejected' | 'ride_cancelled' | 'booking_request' | 'booking_cancelled_by_passenger' | 'group_joined' | 'group_member_joined' | 'pending_approval' | 'default';

/** מיפוי type מהבקאנד לסוג תצוגה (אייקון + סגנון). */
function getDisplayType(type: string): DisplayType {
  if (type === 'booking_confirmed') return 'booking_approved';
  if (type === 'ride_request') return 'booking_request';
  if (type === 'pending_approval') return 'pending_approval';
  const known: DisplayType[] = ['booking_approved', 'booking_rejected', 'ride_cancelled', 'booking_request', 'booking_cancelled_by_passenger', 'group_joined', 'group_member_joined', 'pending_approval'];
  return known.includes(type as DisplayType) ? (type as DisplayType) : 'default';
}

/** קבוצת זמן: היום, אתמול, השבוע, קודם לכן */
function getTimeGroup(date: string): string {
  const d = new Date(date);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dayStart = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.round((today.getTime() - dayStart.getTime()) / (24 * 60 * 60 * 1000));
  if (diffDays === 0) return 'היום';
  if (diffDays === 1) return 'אתמול';
  if (diffDays >= 2 && diffDays < 7) return 'השבוע';
  return 'קודם לכן';
}

const GROUP_ORDER = ['היום', 'אתמול', 'השבוע', 'קודם לכן'];

export default function Notifications() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    markNotificationRead,
    markAllNotificationsRead,
    refreshUnreadNotifications,
    isNotificationRead,
    unreadNotifications,
  } = useChat();
  const [list, setList] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchNotifications = useCallback(async () => {
    if (!user?.user_id) return;
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get<NotificationItem[]>('/users/me/notifications');
      setList(Array.isArray(data) ? data : []);
      refreshUnreadNotifications();
    } catch {
      setError('לא ניתן לטעון את ההתראות');
    } finally {
      setLoading(false);
    }
  }, [user?.user_id, refreshUnreadNotifications]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  useEffect(() => {
    const onRefresh = () => {
      void fetchNotifications();
    };
    window.addEventListener('linkup-notifications-refresh', onRefresh);
    return () => window.removeEventListener('linkup-notifications-refresh', onRefresh);
  }, [fetchNotifications]);

  const grouped = useCallback(() => {
    const groups: Record<string, NotificationItem[]> = {};
    GROUP_ORDER.forEach((g) => { groups[g] = []; });
    list.forEach((n) => {
      const g = getTimeGroup(n.created_at);
      if (!groups[g]) groups[g] = [];
      groups[g].push(n);
    });
    return GROUP_ORDER.filter((g) => groups[g].length > 0).map((g) => ({ label: g, items: groups[g] }));
  }, [list]);

  const handleRowClick = (n: NotificationItem) => {
    const key = getNotificationItemKey(n);
    if (!isNotificationRead(key)) markNotificationRead(key);
    if (n.action_url) navigate(n.action_url);
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <h1 className={styles.pageTitle}>התראות</h1>
        <p className={styles.pageLoading}>טוען...</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.pageTitle}>התראות</h1>
        {unreadNotifications > 0 && (
          <button
            type="button"
            className={styles.markAllRead}
            onClick={() => markAllNotificationsRead()}
          >
            סמן הכל כנקרא
          </button>
        )}
      </header>

      {error && <p className={styles.pageError}>{error}</p>}

      {list.length === 0 ? (
        <div className={styles.empty}>
          <Bell size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <p className={styles.emptyTitle}>אין התראות חדשות</p>
          <p className={styles.emptySub}>כשיהיו פעילויות חדשות, הן יופיעו כאן</p>
        </div>
      ) : (
        <div className={styles.groups}>
          {grouped().map(({ label, items }) => (
            <div key={label} className={styles.group}>
              <h2 className={styles.groupTitle}>{label}</h2>
              {items.map((n) => {
                const key = getNotificationItemKey(n);
                const read = isNotificationRead(key);
                const displayType = getDisplayType(n.type);
                const routeStr = [n.ride_origin, n.ride_destination].filter(Boolean).join(' ← ') || null;
                const bodyLine = n.body && routeStr ? `${n.body} · ${routeStr}` : (n.body || routeStr);
                return (
                  <button
                    key={key}
                    type="button"
                    className={`${styles.notificationRow} ${read ? '' : styles.unread}`}
                    onClick={() => handleRowClick(n)}
                  >
                    <span className={`${styles.notifIcon} ${styles[`icon_${displayType}`]}`}>
                      {displayType === 'booking_approved' && <CheckCircle size={16} />}
                      {displayType === 'booking_rejected' && <XCircle size={16} />}
                      {displayType === 'ride_cancelled' && <AlertTriangle size={16} />}
                      {displayType === 'booking_request' && <UserPlus size={16} />}
                      {displayType === 'booking_cancelled_by_passenger' && <UserMinus size={16} />}
                      {displayType === 'group_joined' && <Users size={16} />}
                      {displayType === 'group_member_joined' && <UserCheck size={16} />}
                      {(displayType === 'pending_approval' || displayType === 'default') && <Bell size={16} />}
                    </span>
                    <div className={styles.notifContent}>
                      <p className={read ? styles.notifTitle : `${styles.notifTitle} ${styles.notifTitleUnread}`}>
                        {n.title}
                      </p>
                      {bodyLine && <p className={styles.notifBody}>{bodyLine}</p>}
                      <p className={styles.notifTime}>{formatDateTimeNoSeconds(n.created_at)}</p>
                    </div>
                    {!read && <span className={styles.unreadDot} aria-hidden />}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
