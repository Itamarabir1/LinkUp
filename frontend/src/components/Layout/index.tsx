import { Outlet, NavLink, Link } from 'react-router-dom';
import { MessageCircle, Bell, User, Search, Plus } from 'lucide-react';
import ChatPopup from '../ChatPopup/ChatPopup';
import { NotificationToast } from '../NotificationToast/NotificationToast';
import { useLayoutShell } from './useLayoutShell';
import styles from './Layout.module.css';

export default function Layout() {
  const {
    openConversationId,
    showChatPopup,
    messagesBadge,
    notificationsBadge,
    profileOpen,
    setProfileOpen,
    profileRef,
    notifPermission,
    handleLogout,
    handleEnableNotifications,
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
            הנסיעות שלי
          </NavLink>
          <NavLink
            to="/my-requests"
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            בקשות טרמפ
          </NavLink>
          <NavLink
            to="/my-bookings"
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            הזמנות שלי
          </NavLink>
          <NavLink
            to="/groups"
            end={false}
            className={({ isActive }) =>
              isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
            }
          >
            קבוצות
          </NavLink>
        </div>

        <div className={styles.navActions}>
          <div className={styles.iconBtnWrapper}>
            <Link to="/messages" className={styles.iconBtn} aria-label="הודעות">
              <MessageCircle size={16} />
              {messagesBadge && (
                <span className={styles.badge} aria-hidden>
                  {messagesBadge}
                </span>
              )}
            </Link>
          </div>
          <div className={styles.iconBtnWrapper}>
            <Link to="/notifications" className={styles.iconBtn} aria-label="התראות">
              <Bell size={16} />
              {notificationsBadge && (
                <span className={styles.badge} aria-hidden>
                  {notificationsBadge}
                </span>
              )}
            </Link>
          </div>
          <div className={styles.profileWrap} ref={profileRef}>
            <button
              type="button"
              className={styles.iconBtn}
              onClick={() => setProfileOpen((o) => !o)}
              aria-label="פרופיל"
              aria-expanded={profileOpen}
              aria-haspopup="true"
            >
              <User size={16} />
            </button>
            {profileOpen && (
              <div className={styles.profileDropdown} role="menu">
                <Link
                  to="/profile"
                  className={styles.profileDropdownItem}
                  onClick={() => setProfileOpen(false)}
                >
                  הפרופיל שלי
                </Link>
                {notifPermission !== 'granted' && (
                  <button
                    type="button"
                    className={styles.profileDropdownItem}
                    onClick={handleEnableNotifications}
                  >
                    {notifPermission === 'denied'
                      ? '🔕 התראות חסומות בדפדפן'
                      : '🔔 הפעל התראות'}
                  </button>
                )}
                <div className={styles.profileDropdownDivider} />
                <button
                  type="button"
                  className={styles.profileDropdownItem}
                  onClick={handleLogout}
                >
                  התנתק
                </button>
              </div>
            )}
          </div>
          <div className={styles.navDivider} />
          <Link to="/search" className={styles.btnSearch}>
            <Search size={14} />
            חפש טרמפ
          </Link>
          <Link to="/create-ride" className={styles.btnCreateRide}>
            <Plus size={14} />
            הצע נסיעה
          </Link>
        </div>
      </nav>
      <main className={styles.main}>
        <Outlet />
      </main>
      {showChatPopup && openConversationId && (
        <ChatPopup conversationId={openConversationId} />
      )}
      <NotificationToast />
    </div>
  );
}
