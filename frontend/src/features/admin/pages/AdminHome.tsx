import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  CartesianGrid, Cell, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useAdminStats } from '../queries/useAdminStats';
import { useAdminHealth } from '../queries/useAdminHealth';
import { useAdminTheme } from '../hooks/useAdminTheme';
import {
  RIDE_STATUS_COLORS, RIDE_STATUS_LABELS,
  BOOKING_STATUS_COLORS, BOOKING_STATUS_LABELS,
} from '../adminConstants';
import page from '../styles/AdminPage.module.css';

function recordToPie(
  record: Record<string, number>,
  colors: Record<string, string>,
  labels: Record<string, string>,
) {
  return Object.entries(record)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: labels[k] ?? k, value: v, fill: colors[k] ?? '#334155' }));
}

function pieLabel(props: { name?: string; percent?: number }) {
  const pct = Math.round((props.percent ?? 0) * 100);
  return pct === 0 ? null : `${props.name} ${pct}%`;
}

function HealthStrip() {
  const { data, isLoading } = useAdminHealth();
  if (isLoading || !data) return null;
  const pills = [
    { label: 'DB', ok: data.database === 'ok' },
    { label: 'Redis', ok: data.redis === 'ok' },
    { label: 'RabbitMQ', ok: data.rabbitmq === 'ok' },
  ];
  return (
    <div className={page.healthStrip}>
      {pills.map((p) => (
        <div
          key={p.label}
          className={`${page.healthPill} ${p.ok ? page.healthPillOk : page.healthPillErr}`}
        >
          <div className={page.healthDot} />
          {p.label} {p.ok ? 'תקין' : 'שגיאה'}
        </div>
      ))}
    </div>
  );
}

export default function AdminHome() {
  const { data, isLoading, isError } = useAdminStats();
  const status = isLoading ? 'loading' : isError ? 'error' : 'ready';
  const { chart } = useAdminTheme();

  const tooltipStyle = {
    backgroundColor: chart.tooltipBg,
    border: `1px solid ${chart.tooltipBorder}`,
    borderRadius: 8,
    color: chart.tooltipColor,
    fontSize: 12,
  };

  const ridePie = useMemo(() =>
    data ? recordToPie(data.rides_by_status, RIDE_STATUS_COLORS, RIDE_STATUS_LABELS) : [],
  [data]);

  const bookingPie = useMemo(() =>
    data ? recordToPie(data.bookings_by_status, BOOKING_STATUS_COLORS, BOOKING_STATUS_LABELS) : [],
  [data]);

  return (
    <div>
      <HealthStrip />

      <div className={page.sectionTitle}>סטטיסטיקות</div>
      <div className={page.statsGrid}>
        <Link to="/admin/users" className={page.statCard}>
          <div className={page.statLabel}>סה"כ משתמשים</div>
          <div className={page.statValue}>{data?.users_total ?? '—'}</div>
          <div className={page.statHint}>כל הזמן</div>
        </Link>
        <Link to="/admin/users" className={`${page.statCard} ${page.statCardToday}`}>
          <div className={page.statLabel}>
            חדשים היום <span className={page.badgeToday}>היום</span>
          </div>
          <div className={page.statValue}>{data?.users_new_today ?? '—'}</div>
          <div className={page.statChangeUp}>↑ משתמשים חדשים</div>
        </Link>
        <Link to="/admin/rides" className={page.statCard}>
          <div className={page.statLabel}>נסיעות פעילות</div>
          <div className={page.statValue}>{data?.rides_active ?? '—'}</div>
          <div className={page.statHint}>open / full / active</div>
        </Link>
        <Link
          to="/admin/lookup"
          className={`${page.statCard} ${(data?.bookings_pending ?? 0) > 0 ? page.statCardWarn : ''}`}
        >
          <div className={page.statLabel}>הזמנות ממתינות</div>
          <div className={`${page.statValue} ${(data?.bookings_pending ?? 0) > 0 ? page.statValueWarn : ''}`}>
            {data?.bookings_pending ?? '—'}
          </div>
          <div className={page.statChangeWarn}>⚠ דורש טיפול</div>
        </Link>
        <Link to="/admin/outbox" className={page.statCard}>
          <div className={page.statLabel}>Outbox ממתינים</div>
          <div className={page.statValue}>{data?.outbox_pending ?? '—'}</div>
          <div className={page.statHint}>תור אירועים</div>
        </Link>
        <Link
          to="/admin/outbox"
          className={`${page.statCard} ${(data?.outbox_failed ?? 0) > 0 ? page.statCardDanger : ''}`}
        >
          <div className={page.statLabel}>Outbox נכשל</div>
          <div className={`${page.statValue} ${(data?.outbox_failed ?? 0) > 0 ? page.statValueDanger : ''}`}>
            {data?.outbox_failed ?? '—'}
          </div>
          <div className={page.statHint}>דורש בדיקה</div>
        </Link>
        <Link to="/admin/users" className={page.statCard}>
          <div className={page.statLabel}>פעילים 7 ימים</div>
          <div className={page.statValue}>{data?.active_users_last_7_days ?? '—'}</div>
          <div className={page.statHint}>לפי פעילות אחרונה</div>
        </Link>
        <Link to="/admin/rides" className={page.statCard}>
          <div className={page.statLabel}>סה"כ נסיעות</div>
          <div className={page.statValue}>{data?.rides_total ?? '—'}</div>
          <div className={page.statHint}>כל הסטטוסים</div>
        </Link>
      </div>

      {status === 'loading' && <p className={page.muted}>טוען נתונים...</p>}
      {status === 'error' && <p className={page.error}>לא ניתן לטעון סטטיסטיקות.</p>}

      {status === 'ready' && data && (
        <>
          <div className={page.sectionTitle} style={{ marginTop: 24 }}>משתמשים חדשים — 7 ימים</div>
          <div className={page.chartCard} style={{ marginBottom: 16 }}>
            <div className={`${page.chartLtr}`} style={{ height: 200 }}>
              {data.users_per_day.every((d) => d.count === 0) ? (
                <p className={page.chartEmpty}>אין נתונים</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.users_per_day} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fill: chart.axis, fontSize: 10 }} />
                    <YAxis tick={{ fill: chart.axis, fontSize: 10 }} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: chart.tooltipColor }}
                      formatter={(v) => [`${Number(v)} משתמשים`, '']}
                      labelFormatter={(l) => `תאריך: ${l}`}
                    />
                    <Line type="monotone" dataKey="count" stroke="#4f6ef7" strokeWidth={2} dot={{ r: 3, fill: '#4f6ef7' }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className={page.grid2} style={{ marginBottom: 16 }}>
            <div className={page.chartCard}>
              <div className={page.chartTitle}>נסיעות לפי סטטוס</div>
              <div className={page.chartLtr} style={{ height: 220 }}>
                {ridePie.length === 0 ? (
                  <p className={page.chartEmpty}>אין נתונים</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={ridePie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={80} innerRadius={40} label={pieLabel} labelLine={false}>
                        {ridePie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle}
                        formatter={(v) => [Number(v), 'נסיעות']} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
            <div className={page.chartCard}>
              <div className={page.chartTitle}>הזמנות לפי סטטוס</div>
              <div className={page.chartLtr} style={{ height: 220 }}>
                {bookingPie.length === 0 ? (
                  <p className={page.chartEmpty}>אין נתונים</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={bookingPie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={80} innerRadius={40} label={pieLabel} labelLine={false}>
                        {bookingPie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle}
                        formatter={(v) => [Number(v), 'הזמנות']} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>

          <div className={page.sectionTitle}>קישורים מהירים</div>
          <div className={page.quickLinks}>
            <Link to="/admin/health" className={page.quickLink}>בריאות מערכת</Link>
            <Link to="/admin/groups" className={page.quickLink}>קבוצות</Link>
            <Link to="/admin/lookup" className={page.quickLink}>חיפוש נסיעה / הזמנה</Link>
            <Link to="/admin/outbox" className={page.quickLink}>Outbox</Link>
          </div>
        </>
      )}
    </div>
  );
}
