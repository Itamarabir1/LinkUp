import { useMemo, useState } from 'react';
import { useAdminBookings } from '../queries/useAdminBookings';
import page from '../styles/AdminPage.module.css';

export default function AdminBookings() {
  const [statusFilter, setStatusFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const limit = 100;
  const params = useMemo(
    () => ({ status: statusFilter || undefined, limit, offset }),
    [statusFilter, offset],
  );
  const { data, isLoading, isError } = useAdminBookings(params);
  const items = data?.items ?? [];

  return (
    <div>
      <h2 className={page.pageTitle}>Bookings</h2>
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
            <option value="confirmed">confirmed</option>
            <option value="rejected">rejected</option>
            <option value="cancelled">cancelled</option>
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
                  <th>Booking</th>
                  <th>Ride</th>
                  <th>Passenger</th>
                  <th>Seats</th>
                  <th>Pickup</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((b) => (
                  <tr key={b.booking_id}>
                    <td title={b.booking_id}>{b.booking_id.slice(0, 8)}…</td>
                    <td title={b.ride_id}>{b.ride_id.slice(0, 8)}…</td>
                    <td title={b.passenger_id}>{b.passenger_id.slice(0, 8)}…</td>
                    <td>{b.num_seats}</td>
                    <td>{b.pickup_name ?? '—'}</td>
                    <td>{b.status}</td>
                    <td>{b.created_at ?? '—'}</td>
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
