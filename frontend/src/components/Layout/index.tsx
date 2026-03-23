import { Outlet, NavLink, Link, useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { MessageCircle, Bell, User, Search, Plus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useChat } from '../../context/ChatContext';
import ChatPopup from '../ChatPopup/ChatPopup';
import { NotificationToast } from '../NotificationToast/NotificationToast';
import { initFCM } from '../../services/fcm';
import styles from './Layout.module.css';

export default function Layout() {
  const { logout } = useAuth();
  const { unreadMessages, unreadNotifications, openConversationId } = useChat();
  const navigate = useNavigate();
  const location = useLocation();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);
  const [notifPermission, setNotifPermission] = useState<NotificationPermission | null>(
    'Notification' in window ? Notification.permission : null
  );

  const showChatPopup = openConversationId && location.pathname !== '/messages';

  const messagesBadge = unreadMessages > 0 ? (unreadMessages >= 10 ? '9+' : String(unreadMessages)) : null;
  const notificationsBadge = unreadNotifications > 0 ? (unreadNotifications >= 10 ? '9+' : String(unreadNotifications)) : null;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'granted') {
      void initFCM();
    }
  }, []);

  const handleLogout = async () => {
    setProfileOpen(false);
    await logout();
    navigate('/login', { replace: true });
  };

  const handleEnableNotifications = async () => {
    await initFCM();
    setNotifPermission(Notification.permission);
    setProfileOpen(false);
  };

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
