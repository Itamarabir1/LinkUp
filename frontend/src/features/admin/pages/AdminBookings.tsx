import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAdminBookings } from '../queries/useAdminBookings';
import page from '../styles/AdminPage.module.css';

export default function AdminBookings() {
  const { t } = useTranslation('admin');
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
      <h2 className={page.pageTitle}>{t('bookings')}</h2>
      <div className={page.toolbar}>
        <label className={page.muted}>
          {t('status_label')}{' '}
          <select
            className={page.select}
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">{t('all')}</option>
            <option value="pending">pending</option>
            <option value="confirmed">confirmed</option>
            <option value="rejected">rejected</option>
            <option value="cancelled">cancelled</option>
          </select>
        </label>
      </div>
      {isLoading && <p className={page.muted}>{t('loading_short')}</p>}
      {isError && <p className={page.error}>{t('load_error')}</p>}
      {!isLoading && !isError && (
        <>
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>{t('booking_label')}</th>
                  <th>{t('ride_label')}</th>
                  <th>Passenger</th>
                  <th>{t('seats')}</th>
                  <th>Pickup</th>
                  <th>{t('status')}</th>
                  <th>{t('created')}</th>
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
              {t('prev')}
            </button>
            <button
              type="button"
              className={page.btnSm}
              disabled={data?.next_offset == null}
              onClick={() => setOffset(data?.next_offset ?? offset)}
            >
              {t('next')}
            </button>
            <span className={page.muted}>
              {t('pagination', { from: offset + 1, to: offset + items.length, total: data?.total ?? 0 })}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
