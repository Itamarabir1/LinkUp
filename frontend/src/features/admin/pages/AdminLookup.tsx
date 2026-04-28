import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { fetchAdminBooking, fetchAdminRide } from '../api/lookup';
import page from '../styles/AdminPage.module.css';
import styles from './AdminLookup.module.css';

export default function AdminLookup() {
  const [rideId, setRideId] = useState('');
  const [bookingId, setBookingId] = useState('');
  const [activeKind, setActiveKind] = useState<'ride' | 'booking' | null>(null);

  const rideMutation = useMutation({
    mutationFn: (id: string) => fetchAdminRide(id),
  });

  const bookingMutation = useMutation({
    mutationFn: (id: string) => fetchAdminBooking(id),
  });

  function run(kind: 'ride' | 'booking') {
    const id = (kind === 'ride' ? rideId : bookingId).trim();
    if (!id) return;
    setActiveKind(kind);
    if (kind === 'ride') {
      rideMutation.mutate(id);
      return;
    }
    bookingMutation.mutate(id);
  }

  const activeMutation = activeKind === 'ride' ? rideMutation : activeKind === 'booking' ? bookingMutation : null;
  const isIdle = activeMutation == null || activeMutation.isIdle;
  const isLoading = activeMutation?.isPending ?? false;
  const isError = activeMutation?.isError ?? false;
  const data = activeMutation?.data?.data;

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
      {isIdle && <p className={page.muted}>הזן מזהה ולחץ שליפה.</p>}
      {isLoading && <p className={page.muted}>טוען…</p>}
      {isError && <p className={page.error}>לא נמצא או שגיאה.</p>}
      {!isIdle && !isLoading && !isError && (
        <pre className={page.preJson}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}
