import { useCallback, useEffect, useState } from 'react';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';
import { fetchAdminRides, postAdminCancelRide, type AdminRideRow } from '../api/rides';
import page from '../styles/AdminPage.module.css';

type State =
  | { status: 'loading' }
  | { status: 'ready'; items: AdminRideRow[] }
  | { status: 'error' };

export default function AdminRides() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [state, setState] = useState<State>({ status: 'loading' });
  const [cancelTarget, setCancelTarget] = useState<AdminRideRow | null>(null);
  const [cancelling, setCancelling] = useState(false);

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

  return (
    <div>
      <h2 className={page.pageTitle}>נסיעות</h2>
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
