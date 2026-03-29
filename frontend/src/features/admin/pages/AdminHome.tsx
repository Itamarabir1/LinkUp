import { useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchAdminStats, type AdminStatsResponse } from '../api/stats';
import page from '../styles/AdminPage.module.css';
import styles from './AdminHome.module.css';

const RIDE_COLORS: Record<string, string> = {
  open: '#3b82f6',
  full: '#f59e0b',
  active: '#10b981',
  completed: '#6366f1',
  cancelled: '#ef4444',
};

const BOOKING_COLORS: Record<string, string> = {
  pending_approval: '#f59e0b',
  confirmed: '#10b981',
  rejected: '#ef4444',
  cancelled: '#94a3b8',
  completed: '#6366f1',
  en_route: '#3b82f6',
  arrived: '#06b6d4',
  trip_in_progress: '#8b5cf6',
};

const RIDE_LABELS: Record<string, string> = {
  open: 'פתוח',
  full: 'מלא',
  active: 'פעיל',
  completed: 'הושלם',
  cancelled: 'בוטל',
};

const BOOKING_LABELS: Record<string, string> = {
  pending_approval: 'ממתין לאישור',
  confirmed: 'מאושר',
  rejected: 'נדחה',
  cancelled: 'בוטל',
  completed: 'הושלם',
  en_route: 'בדרך',
  arrived: 'הגיע',
  trip_in_progress: 'בנסיעה',
};

function subscribeTheme(onChange: () => void) {
  const el = document.documentElement;
  const mo = new MutationObserver(onChange);
  mo.observe(el, { attributes: true, attributeFilter: ['data-theme'] });
  return () => mo.disconnect();
}

function themeSnapshot() {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

function useDataTheme() {
  return useSyncExternalStore(subscribeTheme, themeSnapshot, () => 'light');
}

function recordToPie(
  record: Record<string, number>,
  colors: Record<string, string>,
  labels: Record<string, string>,
) {
  return Object.entries(record)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({
      name: labels[k] ?? k,
      value: v,
      fill: colors[k] ?? '#94a3b8',
    }));
}

function pieLabel(props: { name?: string; percent?: number }) {
  const pct = Math.round((props.percent ?? 0) * 100);
  if (pct === 0) return null;
  return `${props.name ?? ''} ${pct}%`;
}

type State =
  | { status: 'loading' }
  | { status: 'ready'; data: AdminStatsResponse }
  | { status: 'error' };

export default function AdminHome() {
  const [state, setState] = useState<State>({ status: 'loading' });
  const dataTheme = useDataTheme();
  const isDark = dataTheme === 'dark';

  const chartTheme = useMemo(
    () =>
      isDark
        ? {
            axis: '#94a3b8',
            grid: '#334155',
            tooltipBg: '#1e293b',
            tooltipBorder: '#334155',
            tooltipColor: '#e2e8f0',
          }
        : {
            axis: '#64748b',
            grid: '#e2e8f0',
            tooltipBg: '#ffffff',
            tooltipBorder: '#e2e8f0',
            tooltipColor: '#0f172a',
          },
    [isDark],
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await fetchAdminStats();
        if (!mounted) return;
        setState({ status: 'ready', data });
      } catch {
        if (!mounted) return;
        setState({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const tooltipStyle = {
    backgroundColor: chartTheme.tooltipBg,
    border: `1px solid ${chartTheme.tooltipBorder}`,
    borderRadius: 8,
    color: chartTheme.tooltipColor,
  };

  return (
    <div>
      <h2 className={page.pageTitle}>לוח בקרה</h2>
      <p className={styles.intro}>
        סקירה מהירה של מצב המערכת. לחיצה על כרטיס מובילה למסך הרלוונטי.
      </p>

      {state.status === 'loading' && <p className={page.muted}>טוען נתונים…</p>}
      {state.status === 'error' && (
        <p className={page.error}>לא ניתן לטעון סטטיסטיקות.</p>
      )}
      {state.status === 'ready' && (
        <>
          <div className={styles.statsGrid}>
            <Link to="/admin/users" className={styles.statCard}>
              <p className={styles.statLabel}>סה״כ משתמשים</p>
              <p className={styles.statValue}>{state.data.users_total}</p>
              <p className={styles.statHint}>ניהול משתמשים ←</p>
            </Link>

            <Link to="/admin/users" className={`${styles.statCard} ${styles.statCardToday}`}>
              <p className={styles.statLabel}>
                נרשמו היום <span className={styles.badgeToday}>היום</span>
              </p>
              <p className={styles.statValue}>{state.data.users_new_today}</p>
              <p className={styles.statHint}>משתמשים חדשים</p>
            </Link>

            <Link to="/admin/users" className={styles.statCard}>
              <p className={styles.statLabel}>פעילים 7 ימים</p>
              <p className={styles.statValue}>{state.data.active_users_last_7_days}</p>
              <p className={styles.statHint}>לפי פעילות אחרונה</p>
            </Link>

            <Link to="/admin/rides" className={styles.statCard}>
              <p className={styles.statLabel}>נסיעות פעילות</p>
              <p className={styles.statValue}>{state.data.rides_active}</p>
              <p className={styles.statHint}>open / full / active</p>
            </Link>

            <Link to="/admin/rides" className={styles.statCard}>
              <p className={styles.statLabel}>סה״כ נסיעות</p>
              <p className={styles.statValue}>{state.data.rides_total}</p>
              <p className={styles.statHint}>כל הסטטוסים</p>
            </Link>

            <Link
              to="/admin/lookup"
              className={`${styles.statCard} ${state.data.bookings_pending > 0 ? styles.statCardWarn : ''}`}
            >
              <p className={styles.statLabel}>הזמנות ממתינות</p>
              <p
                className={`${styles.statValue} ${state.data.bookings_pending > 0 ? styles.statValueWarn : ''}`}
              >
                {state.data.bookings_pending}
              </p>
              <p className={styles.statHint}>ממתין לאישור</p>
            </Link>

            <Link to="/admin/outbox" className={styles.statCard}>
              <p className={styles.statLabel}>Outbox ממתין</p>
              <p className={styles.statValue}>{state.data.outbox_pending}</p>
              <p className={styles.statHint}>תור אירועים</p>
            </Link>

            <Link
              to="/admin/outbox"
              className={`${styles.statCard} ${state.data.outbox_failed > 0 ? styles.statCardDanger : ''}`}
            >
              <p className={styles.statLabel}>Outbox נכשל</p>
              <p
                className={`${styles.statValue} ${state.data.outbox_failed > 0 ? styles.statValueDanger : ''}`}
              >
                {state.data.outbox_failed}
              </p>
              <p className={styles.statHint}>דורש טיפול</p>
            </Link>
          </div>

          <h3 className={styles.sectionTitle}>משתמשים חדשים (7 ימים)</h3>
          <div className={styles.chartCard}>
            <div dir="ltr" className={styles.chartLtr}>
              {state.data.users_per_day.every((d) => d.count === 0) ? (
                <p className={styles.chartEmpty}>אין נתונים</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={state.data.users_per_day}>
                    <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fill: chartTheme.axis, fontSize: 12 }} />
                    <YAxis tick={{ fill: chartTheme.axis, fontSize: 12 }} allowDecimals={false} />
                    <Tooltip
                      contentStyle={tooltipStyle}
                      labelStyle={{ color: chartTheme.tooltipColor }}
                      formatter={(value) => {
                        const n = typeof value === 'number' ? value : Number(value);
                        return [`${Number.isFinite(n) ? n : 0} משתמשים`, ''];
                      }}
                      labelFormatter={(label) => `תאריך: ${label}`}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className={`${page.grid2} ${styles.pieRow}`}>
            <div className={styles.chartCard}>
              <h4 className={styles.chartTitle}>נסיעות לפי סטטוס</h4>
              <div dir="ltr" className={styles.chartLtr}>
                {(() => {
                  const pieData = recordToPie(
                    state.data.rides_by_status,
                    RIDE_COLORS,
                    RIDE_LABELS,
                  );
                  const total = pieData.reduce((s, d) => s + d.value, 0);
                  if (total === 0) {
                    return <p className={styles.chartEmpty}>אין נתונים</p>;
                  }
                  return (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={88}
                          label={pieLabel}
                        >
                          {pieData.map((entry, i) => (
                            <Cell key={`${entry.name}-${i}`} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={tooltipStyle}
                          formatter={(value) => {
                            const n = typeof value === 'number' ? value : Number(value);
                            return [Number.isFinite(n) ? n : 0, 'נסיעות'];
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  );
                })()}
              </div>
            </div>
            <div className={styles.chartCard}>
              <h4 className={styles.chartTitle}>הזמנות לפי סטטוס</h4>
              <div dir="ltr" className={styles.chartLtr}>
                {(() => {
                  const pieData = recordToPie(
                    state.data.bookings_by_status,
                    BOOKING_COLORS,
                    BOOKING_LABELS,
                  );
                  const total = pieData.reduce((s, d) => s + d.value, 0);
                  if (total === 0) {
                    return <p className={styles.chartEmpty}>אין נתונים</p>;
                  }
                  return (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie
                          data={pieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={88}
                          label={pieLabel}
                        >
                          {pieData.map((entry, i) => (
                            <Cell key={`${entry.name}-${i}`} fill={entry.fill} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={tooltipStyle}
                          formatter={(value) => {
                            const n = typeof value === 'number' ? value : Number(value);
                            return [Number.isFinite(n) ? n : 0, 'הזמנות'];
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  );
                })()}
              </div>
            </div>
          </div>
        </>
      )}

      <h3 className={styles.sectionTitle}>קישורים מהירים</h3>
      <div className={styles.quickLinks}>
        <Link to="/admin/health" className={styles.quickLink}>
          בריאות מערכת
        </Link>
        <Link to="/admin/groups" className={styles.quickLink}>
          קבוצות
        </Link>
        <Link to="/admin/lookup" className={styles.quickLink}>
          חיפוש נסיעה / הזמנה
        </Link>
      </div>
    </div>
  );
}
