import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  Building2,
  CarFront,
  LayoutDashboard,
  LogOut,
  Search,
  Users,
  Inbox,
} from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import shell from '../styles/AdminShell.module.css';

const nav: Array<{
  to: string;
  end?: boolean;
  label: string;
  icon: typeof LayoutDashboard;
}> = [
  { to: '/admin', end: true, label: 'לוח בקרה', icon: LayoutDashboard },
  { to: '/admin/health', label: 'בריאות', icon: Activity },
  { to: '/admin/users', label: 'משתמשים', icon: Users },
  { to: '/admin/rides', label: 'נסיעות', icon: CarFront },
  { to: '/admin/groups', label: 'קבוצות', icon: Building2 },
  { to: '/admin/outbox', label: 'Outbox', icon: Inbox },
  { to: '/admin/lookup', label: 'חיפוש', icon: Search },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  const pageTitle =
    nav.find((n) => (n.end ? location.pathname === n.to : location.pathname.startsWith(n.to)))
      ?.label ?? 'ניהול';

  return (
    <div className={shell.shell} dir="rtl">
      <aside className={shell.sidebar}>
        <div className={shell.sidebarBrand}>Linkup Admin</div>
        <nav className={shell.nav} aria-label="ניווט ניהול">
          {nav.map(({ to, end, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `${shell.navLink} ${isActive ? shell.navLinkActive : ''}`
              }
            >
              <Icon className={shell.navIcon} size={18} strokeWidth={2} aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className={shell.main}>
        <header className={shell.topbar}>
          <div className={shell.topbarLeft}>
            <h1 className={shell.topbarTitle}>{pageTitle}</h1>
          </div>
          <div className={shell.topbarMeta}>
            <span>
              מחובר: <strong>{user?.full_name}</strong> ({user?.email ?? '—'})
            </span>
            <button type="button" className={shell.logoutBtn} onClick={() => void handleLogout()}>
              <LogOut size={14} className={shell.logoutIcon} aria-hidden />
              יציאה
            </button>
          </div>
        </header>
        <main className={shell.content}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
