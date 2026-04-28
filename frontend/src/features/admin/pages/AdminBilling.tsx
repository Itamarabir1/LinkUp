import { useMemo, useState } from 'react';
import { useAdminBilling } from '../queries/useAdminBilling';
import page from '../styles/AdminPage.module.css';

export default function AdminBilling() {
  const [statusFilter, setStatusFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const limit = 100;
  const params = useMemo(
    () => ({ status: statusFilter || undefined, limit, offset }),
    [statusFilter, offset],
  );
  const { data, isLoading, isError } = useAdminBilling(params);
  const items = data?.items ?? [];

  return (
    <div>
      <h2 className={page.pageTitle}>Billing</h2>
      <div className={page.toolbar}>
        <label className={page.muted}>
          סטטוס:{' '}
          <select
            className={page.select}
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">הכל</option>
            <option value="pending">pending</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
            <option value="canceled">canceled</option>
          </select>
        </label>
      </div>

      {isLoading && <p className={page.muted}>טוען…</p>}
      {isError && <p className={page.error}>שגיאה בטעינה.</p>}
      {!isLoading && !isError && (
        <>
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>Payment</th>
                  <th>User</th>
                  <th>Amount</th>
                  <th>Currency</th>
                  <th>Status</th>
                  <th>Session</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.payment_id}>
                    <td title={p.payment_id}>{p.payment_id.slice(0, 8)}…</td>
                    <td title={p.user_id}>{p.user_id.slice(0, 8)}…</td>
                    <td>{p.amount}</td>
                    <td>{p.currency}</td>
                    <td>{p.status}</td>
                    <td>{p.stripe_session_id ? `${p.stripe_session_id.slice(0, 12)}…` : '—'}</td>
                    <td>{p.created_at ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className={page.toolbar}>
            <button
              type="button"
              className={page.btnSm}
              disabled={offset === 0}
              onClick={() => setOffset((v) => Math.max(0, v - limit))}
            >
              הקודם
            </button>
            <button
              type="button"
              className={page.btnSm}
              disabled={data?.next_offset == null}
              onClick={() => setOffset(data?.next_offset ?? offset)}
            >
              הבא
            </button>
            <span className={page.muted}>
              {offset + 1}-{offset + items.length} מתוך {data?.total ?? 0}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
