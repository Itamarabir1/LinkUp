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
import { getNotificationItemKey } from '../context/ChatContext';
import { formatDateTimeNoSeconds } from '../utils/date';
import { getDisplayType } from './notifications.utils';
import ErrorBanner from '../components/ErrorBanner';
import { useNotifications } from './useNotifications';
import styles from './Notifications.module.css';

export default function Notifications() {
  const {
    loading,
    error,
    list,
    grouped,
    handleRowClick,
    unreadNotifications,
    markAllNotificationsRead,
    isNotificationRead,
  } = useNotifications();

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
            onClick={markAllNotificationsRead}
          >
            סמן הכל כנקרא
          </button>
        )}
      </header>

      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

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
