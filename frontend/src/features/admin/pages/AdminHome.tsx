import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('admin');
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
          {p.label} {p.ok ? t('ok') : t('error')}
        </div>
      ))}
    </div>
  );
}

export default function AdminHome() {
  const { t } = useTranslation('admin');
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

      <div className={page.sectionTitle}>{t('statistics')}</div>
      <div className={page.statsGrid}>
        <Link to="/admin/users" className={page.statCard}>
          <div className={page.statLabel}>{t('total_users')}</div>
          <div className={page.statValue}>{data?.users_total ?? '—'}</div>
          <div className={page.statHint}>{t('all_time')}</div>
        </Link>
        <Link to="/admin/users" className={`${page.statCard} ${page.statCardToday}`}>
          <div className={page.statLabel}>
            {t('new_today')} <span className={page.badgeToday}>{t('today_badge')}</span>
          </div>
          <div className={page.statValue}>{data?.users_new_today ?? '—'}</div>
          <div className={page.statChangeUp}>↑ {t('new_users')}</div>
        </Link>
        <Link to="/admin/rides" className={page.statCard}>
          <div className={page.statLabel}>{t('active_rides')}</div>
          <div className={page.statValue}>{data?.rides_active ?? '—'}</div>
          <div className={page.statHint}>open / full / active</div>
        </Link>
        <Link
          to="/admin/lookup"
          className={`${page.statCard} ${(data?.bookings_pending ?? 0) > 0 ? page.statCardWarn : ''}`}
        >
          <div className={page.statLabel}>{t('pending_bookings')}</div>
          <div className={`${page.statValue} ${(data?.bookings_pending ?? 0) > 0 ? page.statValueWarn : ''}`}>
            {data?.bookings_pending ?? '—'}
          </div>
          <div className={page.statChangeWarn}>⚠ {t('needs_attention')}</div>
        </Link>
        <Link to="/admin/outbox" className={page.statCard}>
          <div className={page.statLabel}>{t('outbox_pending')}</div>
          <div className={page.statValue}>{data?.outbox_pending ?? '—'}</div>
          <div className={page.statHint}>{t('event_queue')}</div>
        </Link>
        <Link
          to="/admin/outbox"
          className={`${page.statCard} ${(data?.outbox_failed ?? 0) > 0 ? page.statCardDanger : ''}`}
        >
          <div className={page.statLabel}>{t('outbox_failed')}</div>
          <div className={`${page.statValue} ${(data?.outbox_failed ?? 0) > 0 ? page.statValueDanger : ''}`}>
            {data?.outbox_failed ?? '—'}
          </div>
          <div className={page.statHint}>{t('needs_review')}</div>
        </Link>
        <Link to="/admin/users" className={page.statCard}>
          <div className={page.statLabel}>{t('active_7_days')}</div>
          <div className={page.statValue}>{data?.active_users_last_7_days ?? '—'}</div>
          <div className={page.statHint}>{t('by_recent_activity')}</div>
        </Link>
        <Link to="/admin/rides" className={page.statCard}>
          <div className={page.statLabel}>{t('total_rides')}</div>
          <div className={page.statValue}>{data?.rides_total ?? '—'}</div>
          <div className={page.statHint}>{t('all_statuses')}</div>
        </Link>
      </div>

      {status === 'loading' && <p className={page.muted}>{t('loading_data')}</p>}
      {status === 'error' && <p className={page.error}>{t('could_not_load_stats')}</p>}

      {status === 'ready' && data && (
        <>
          <div className={page.sectionTitle} style={{ marginTop: 24 }}>{t('new_users_7_days')}</div>
          <div className={page.chartCard} style={{ marginBottom: 16 }}>
            <div className={`${page.chartLtr}`} style={{ height: 200 }}>
              {data.users_per_day.every((d) => d.count === 0) ? (
                <p className={page.chartEmpty}>{t('no_data')}</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.users_per_day} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fill: chart.axis, fontSize: 10 }} />
                    <YAxis tick={{ fill: chart.axis, fontSize: 10 }} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: chart.tooltipColor }}
                      formatter={(v) => [`${Number(v)} ${t('users_tooltip')}`, '']}
                      labelFormatter={(l) => t('date_label', { date: l })}
                    />
                    <Line type="monotone" dataKey="count" stroke="#4f6ef7" strokeWidth={2} dot={{ r: 3, fill: '#4f6ef7' }} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className={page.grid2} style={{ marginBottom: 16 }}>
            <div className={page.chartCard}>
              <div className={page.chartTitle}>{t('rides_by_status')}</div>
              <div className={page.chartLtr} style={{ height: 220 }}>
                {ridePie.length === 0 ? (
                  <p className={page.chartEmpty}>{t('no_data')}</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={ridePie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={80} innerRadius={40} label={pieLabel} labelLine={false}>
                        {ridePie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle}
                        formatter={(v) => [Number(v), t('rides_tooltip')]} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
            <div className={page.chartCard}>
              <div className={page.chartTitle}>{t('bookings_by_status')}</div>
              <div className={page.chartLtr} style={{ height: 220 }}>
                {bookingPie.length === 0 ? (
                  <p className={page.chartEmpty}>{t('no_data')}</p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={bookingPie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={80} innerRadius={40} label={pieLabel} labelLine={false}>
                        {bookingPie.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle}
                        formatter={(v) => [Number(v), t('bookings_tooltip')]} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>

          <div className={page.sectionTitle}>{t('quick_links')}</div>
          <div className={page.quickLinks}>
            <Link to="/admin/health" className={page.quickLink}>{t('system_health')}</Link>
            <Link to="/admin/groups" className={page.quickLink}>{t('groups')}</Link>
            <Link to="/admin/lookup" className={page.quickLink}>{t('search_ride_booking')}</Link>
            <Link to="/admin/outbox" className={page.quickLink}>Outbox</Link>
          </div>
        </>
      )}
    </div>
  );
}
