import { useMemo, useState } from 'react';
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
import type { AdminRideRow } from '../api/rides';
import { useAdminStats } from '../queries/useAdminStats';
import { useAdminRides } from '../queries/useAdminRides';
import { useCancelAdminRide } from '../mutations/useAdminRideMutations';
import { useAdminTheme } from '../hooks/useAdminTheme';
import { RIDE_STATUS_COLORS, RIDE_STATUS_LABELS } from '../adminConstants';
import page from '../styles/AdminPage.module.css';

export default function AdminRides() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [cancelTarget, setCancelTarget] = useState<AdminRideRow | null>(null);
  const { chart: chartTheme } = useAdminTheme();
  const { data: statsData } = useAdminStats();
  const { data, isLoading, isError } = useAdminRides({
    status: statusFilter || undefined,
    limit: 150,
  });
  const items = data ?? [];
  const cancelRide = useCancelAdminRide();
  const status: 'loading' | 'error' | 'ready' = isLoading ? 'loading' : isError ? 'error' : 'ready';

  const barData = useMemo(() => {
    const ridesByStatus = statsData?.rides_by_status ?? {};
    return Object.entries(ridesByStatus).map(([key, count]) => ({
      statusKey: key,
      name: RIDE_STATUS_LABELS[key] ?? key,
      count,
    }));
  }, [statsData]);

  const barTotal = useMemo(() => barData.reduce((s, d) => s + d.count, 0), [barData]);

  async function confirmCancel() {
    if (!cancelTarget) return;
    try {
      await cancelRide.mutateAsync(cancelTarget.ride_id);
      setCancelTarget(null);
    } catch {
      // toast handled in mutation hook
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

      {!statsData && (
        <p className={page.muted}>טוען חלוקה לפי סטטוס…</p>
      )}
      {statsData && (
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
                        fill={RIDE_STATUS_COLORS[entry.statusKey] ?? '#94a3b8'}
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

      {status === 'loading' && <p className={page.muted}>טוען…</p>}
      {status === 'error' && <p className={page.error}>שגיאה בטעינה.</p>}
      {status === 'ready' && (
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
              {items.map((r) => (
                <tr key={r.ride_id}>
                  <td title={r.ride_id}>{r.ride_id.slice(0, 8)}…</td>
                  <td>
                    <div className={page.userCell}>
                      <div className={page.avatar}>{(r.driver_name || '?').charAt(0)}</div>
                      <span className={page.userName}>{r.driver_name || r.driver_id.slice(0, 8)}</span>
                    </div>
                  </td>
                  <td>{r.origin_name ?? '—'}</td>
                  <td>{r.destination_name ?? '—'}</td>
                  <td>{r.departure_time ?? '—'}</td>
                  <td>{r.status}</td>
                  <td>{r.available_seats}</td>
                  <td className={page.actionsCell}>
                    <button
                      type="button"
                      className={page.btnSmDanger}
                      disabled={r.status === 'cancelled' || cancelRide.isPending}
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
        onClose={() => !cancelRide.isPending && setCancelTarget(null)}
        title="ביטול נסיעה"
        description={
          cancelTarget
            ? `לבטל נסיעה מ-${cancelTarget.origin_name ?? '?'} ל-${cancelTarget.destination_name ?? '?'}?`
            : undefined
        }
        confirmLabel="בטל נסיעה"
        variant="danger"
        loading={cancelRide.isPending}
        onConfirm={confirmCancel}
      />
    </div>
  );
}
