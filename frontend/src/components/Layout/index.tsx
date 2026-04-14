import { Outlet, NavLink, Link } from 'react-router-dom';
import { MessageCircle, Bell, User, Search, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ChatPopup from '../ChatPopup/ChatPopup';
import { useLayoutShell } from './useLayoutShell';
import styles from './Layout.module.css';

export default function Layout() {
  const { t } = useTranslation('nav');
  const {
    openConversationId,
    showChatPopup,
    messagesBadge,
    notificationsBadge,
  } = useLayoutShell();

  return (
    <div className={styles.layout}>
      <nav className={styles.nav}>
        <div className={styles.navTabs}>
          <NavLink
            to="/my-rides"
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            {t('myRides')}
          </NavLink>
          <NavLink
            to="/my-requests"
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            {t('myRequests')}
          </NavLink>
          <NavLink
            to="/my-bookings"
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            {t('myBookings')}
          </NavLink>
          <NavLink
            to="/groups"
            end={false}
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            {t('groups')}
          </NavLink>
        </div>

        <div className={styles.navActions}>
          <div className={styles.iconBtnWrapper}>
            <Link to="/messages" className={styles.iconBtn} aria-label={t('messages')}>
              <MessageCircle size={16} />
              {messagesBadge && (
                <span className={styles.badge} aria-hidden>
                  {messagesBadge}
                </span>
              )}
            </Link>
          </div>
          <div className={styles.iconBtnWrapper}>
            <Link to="/notifications" className={styles.iconBtn} aria-label={t('notifications')} title={t('notifications')}>
              <Bell size={16} />
              {notificationsBadge && (
                <span className={styles.badge} aria-hidden>
                  {notificationsBadge}
                </span>
              )}
            </Link>
          </div>
          <div className={styles.iconBtnWrapper}>
            <Link
              to="/profile"
              className={styles.iconBtn}
              aria-label={t('profile')}
              title={t('profile')}
            >
              <User size={16} />
            </Link>
          </div>
          <div className={styles.navDivider} />
          <Link to="/search" className={styles.btnSearch}>
            <Search size={14} />
            {t('searchRide')}
          </Link>
          <Link to="/create-ride" className={styles.btnCreateRide}>
            <Plus size={14} />
            {t('createRide')}
          </Link>
        </div>
      </nav>
      <main className={styles.main}>
        <Outlet />
      </main>
      {showChatPopup && openConversationId && (
        <ChatPopup conversationId={openConversationId} />
      )}
    </div>
  );
}
