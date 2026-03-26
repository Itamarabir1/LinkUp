import { useState } from 'react';
import { fetchAdminBooking, fetchAdminRide } from '../api/lookup';
import page from '../styles/AdminPage.module.css';
import styles from './AdminLookup.module.css';

type Result = { status: 'idle' | 'loading' | 'ready' | 'error'; data?: unknown };

export default function AdminLookup() {
  const [rideId, setRideId] = useState('');
  const [bookingId, setBookingId] = useState('');
  const [result, setResult] = useState<Result>({ status: 'idle' });

  async function run(kind: 'ride' | 'booking') {
    setResult({ status: 'loading' });
    try {
      const id = (kind === 'ride' ? rideId : bookingId).trim();
      const res = kind === 'ride' ? await fetchAdminRide(id) : await fetchAdminBooking(id);
      setResult({ status: 'ready', data: res.data });
    } catch {
      setResult({ status: 'error' });
    }
  }

  return (
    <div>
      <h2 className={page.pageTitle}>חיפוש לפי מזהה</h2>
      <div className={styles.grid}>
        <div>
          <h3 className={styles.blockTitle}>נסיעה</h3>
          <input
            className={styles.field}
            value={rideId}
            onChange={(e) => setRideId(e.target.value)}
            placeholder="ride_id (UUID)"
          />
          <div className={styles.rowActions}>
            <button
              type="button"
              className={page.btnSmPrimary}
              onClick={() => void run('ride')}
              disabled={!rideId.trim()}
            >
              שליפה
            </button>
          </div>
        </div>
        <div>
          <h3 className={styles.blockTitle}>הזמנה</h3>
          <input
            className={styles.field}
            value={bookingId}
            onChange={(e) => setBookingId(e.target.value)}
            placeholder="booking_id (UUID)"
          />
          <div className={styles.rowActions}>
            <button
              type="button"
              className={page.btnSmPrimary}
              onClick={() => void run('booking')}
              disabled={!bookingId.trim()}
            >
              שליפה
            </button>
          </div>
        </div>
      </div>
      <h3 className={styles.resultTitle}>תוצאה</h3>
      {result.status === 'idle' && <p className={page.muted}>הזן מזהה ולחץ שליפה.</p>}
      {result.status === 'loading' && <p className={page.muted}>טוען…</p>}
      {result.status === 'error' && <p className={page.error}>לא נמצא או שגיאה.</p>}
      {result.status === 'ready' && (
        <pre className={page.preJson}>{JSON.stringify(result.data, null, 2)}</pre>
      )}
    </div>
  );
}
