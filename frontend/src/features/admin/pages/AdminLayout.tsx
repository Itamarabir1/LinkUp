import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  Building2,
  BookCheck,
  CarFront,
  Cpu,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Search,
  ShieldCheck,
  Users,
  Inbox,
} from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import shell from '../styles/AdminShell.module.css';

const navItems: Array<{
  to: string;
  end?: boolean;
  labelKey: string;
  icon: typeof LayoutDashboard;
}> = [
  { to: '/admin', end: true, labelKey: 'dashboard', icon: LayoutDashboard },
  { to: '/admin/health', labelKey: 'health', icon: Activity },
  { to: '/admin/users', labelKey: 'users', icon: Users },
  { to: '/admin/rides', labelKey: 'rides', icon: CarFront },
  { to: '/admin/bookings', labelKey: 'bookings', icon: BookCheck },
  { to: '/admin/groups', labelKey: 'groups', icon: Building2 },
  { to: '/admin/billing', labelKey: 'billing', icon: CreditCard },
  { to: '/admin/audit', labelKey: 'audit', icon: ShieldCheck },
  { to: '/admin/outbox', labelKey: 'outbox', icon: Inbox },
  { to: '/admin/ops', labelKey: 'ops', icon: Cpu },
  { to: '/admin/lookup', labelKey: 'search', icon: Search },
];

export default function AdminLayout() {
  const { t } = useTranslation('admin');
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  const activeItem = navItems.find((n) =>
    n.end ? location.pathname === n.to : location.pathname.startsWith(n.to),
  );
  const pageTitle = activeItem ? t(activeItem.labelKey) : t('admin');

  return (
    <div className={shell.shell} dir="rtl">
      <aside className={shell.sidebar}>
        <div className={shell.sidebarBrand}>LinkUp Admin</div>
        <nav className={shell.nav} aria-label={t('admin_nav')}>
          {navItems.map(({ to, end, labelKey, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `${shell.navLink} ${isActive ? shell.navLinkActive : ''}`
              }
            >
              <Icon className={shell.navIcon} size={18} strokeWidth={2} aria-hidden />
              {t(labelKey)}
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
              {t('logged_in')} <strong>{user?.full_name}</strong> ({user?.email ?? '—'})
            </span>
            <button type="button" className={shell.logoutBtn} onClick={() => void handleLogout()}>
              <LogOut size={14} className={shell.logoutIcon} aria-hidden />
              {t('sign_out')}
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
