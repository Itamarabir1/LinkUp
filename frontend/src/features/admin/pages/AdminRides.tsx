import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';
import { fetchAdminStats } from '../api/stats';
import { fetchAdminRides, postAdminCancelRide, type AdminRideRow } from '../api/rides';
import page from '../styles/AdminPage.module.css';

const RIDE_COLORS: Record<string, string> = {
  open: '#3b82f6',
  full: '#f59e0b',
  active: '#10b981',
  completed: '#6366f1',
  cancelled: '#ef4444',
};

const RIDE_LABELS: Record<string, string> = {
  open: 'פתוח',
  full: 'מלא',
  active: 'פעיל',
  completed: 'הושלם',
  cancelled: 'בוטל',
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

type State =
  | { status: 'loading' }
  | { status: 'ready'; items: AdminRideRow[] }
  | { status: 'error' };

type ChartState =
  | { status: 'loading' }
  | { status: 'ready'; rides_by_status: Record<string, number> }
  | { status: 'error' };

export default function AdminRides() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [state, setState] = useState<State>({ status: 'loading' });
  const [chartState, setChartState] = useState<ChartState>({ status: 'loading' });
  const [cancelTarget, setCancelTarget] = useState<AdminRideRow | null>(null);
  const [cancelling, setCancelling] = useState(false);
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
        setChartState({ status: 'ready', rides_by_status: data.rides_by_status ?? {} });
      } catch {
        if (!mounted) return;
        setChartState({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const barData = useMemo(() => {
    if (chartState.status !== 'ready') return [];
    return Object.entries(chartState.rides_by_status).map(([key, count]) => ({
      statusKey: key,
      name: RIDE_LABELS[key] ?? key,
      count,
    }));
  }, [chartState]);

  const barTotal = useMemo(() => barData.reduce((s, d) => s + d.count, 0), [barData]);

  const load = useCallback(async () => {
    setState({ status: 'loading' });
    try {
      const { data } = await fetchAdminRides({
        status: statusFilter || undefined,
        limit: 150,
      });
      setState({ status: 'ready', items: Array.isArray(data) ? data : [] });
    } catch {
      setState({ status: 'error' });
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function confirmCancel() {
    if (!cancelTarget) return;
    setCancelling(true);
    try {
      await postAdminCancelRide(cancelTarget.ride_id);
      triggerNotificationToast({ title: 'בוצע', body: 'הנסיעה בוטלה.' });
      setCancelTarget(null);
      await load();
    } catch {
      triggerNotificationToast({ title: 'שגיאה', body: 'לא ניתן לבטל את הנסיעה.' });
    } finally {
      setCancelling(false);
    }
  }

  const tooltipStyle = {
    backgroundColor: chartTheme.tooltipBg,
    border: `1px solid ${chartTheme.tooltipBorder}`,
    borderRadius: 8,
    color: chartTheme.tooltipColor,
  };

  return (
    <div>
      <h2 className={page.pageTitle}>נסיעות</h2>

      {chartState.status === 'loading' && (
        <p className={page.muted}>טוען חלוקה לפי סטטוס…</p>
      )}
      {chartState.status === 'error' && null}
      {chartState.status === 'ready' && (
        <div className={page.chartMiniWrap}>
          <div dir="ltr">
            {barTotal === 0 ? (
              <p className={page.chartMiniEmpty}>אין נתונים</p>
            ) : (
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={barData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke={chartTheme.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: chartTheme.axis, fontSize: 11 }}
                    interval={0}
                    angle={-25}
                    textAnchor="end"
                    height={48}
                  />
                  <YAxis tick={{ fill: chartTheme.axis, fontSize: 11 }} allowDecimals={false} width={32} />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(value) => {
                      const n = typeof value === 'number' ? value : Number(value);
                      return [Number.isFinite(n) ? n : 0, 'נסיעות'];
                    }}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {barData.map((entry, i) => (
                      <Cell
                        key={`${entry.statusKey}-${i}`}
                        fill={RIDE_COLORS[entry.statusKey] ?? '#94a3b8'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}

      <div className={page.toolbar}>
        <label className={page.muted}>
          סטטוס:{' '}
          <select
            className={page.select}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">הכל</option>
            <option value="active">פעיל</option>
            <option value="completed">הושלם</option>
            <option value="cancelled">בוטל</option>
          </select>
        </label>
      </div>

      {state.status === 'loading' && <p className={page.muted}>טוען…</p>}
      {state.status === 'error' && <p className={page.error}>שגיאה בטעינה.</p>}
      {state.status === 'ready' && (
        <div className={page.tableWrap}>
          <table className={page.table}>
            <thead>
              <tr>
                <th>מזהה</th>
                <th>נהג</th>
                <th>מוצא</th>
                <th>יעד</th>
                <th>יציאה</th>
                <th>סטטוס</th>
                <th>מושבים</th>
                <th>פעולות</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((r) => (
                <tr key={r.ride_id}>
                  <td title={r.ride_id}>{r.ride_id.slice(0, 8)}…</td>
                  <td>{r.driver_name || r.driver_id.slice(0, 8)}</td>
                  <td>{r.origin_name ?? '—'}</td>
                  <td>{r.destination_name ?? '—'}</td>
                  <td>{r.departure_time ?? '—'}</td>
                  <td>{r.status}</td>
                  <td>{r.available_seats}</td>
                  <td className={page.actionsCell}>
                    <button
                      type="button"
                      className={page.btnSmDanger}
                      disabled={r.status === 'cancelled' || cancelling}
                      onClick={() => setCancelTarget(r)}
                    >
                      ביטול נסיעה
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmModal
        open={cancelTarget !== null}
        onClose={() => !cancelling && setCancelTarget(null)}
        title="ביטול נסיעה"
        description={
          cancelTarget
            ? `לבטל נסיעה מ-${cancelTarget.origin_name ?? '?'} ל-${cancelTarget.destination_name ?? '?'}?`
            : undefined
        }
        confirmLabel="בטל נסיעה"
        variant="danger"
        loading={cancelling}
        onConfirm={confirmCancel}
      />
    </div>
  );
}
