import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { fetchAdminBooking, fetchAdminRide } from '../api/lookup';
import page from '../styles/AdminPage.module.css';
import styles from './AdminLookup.module.css';

export default function AdminLookup() {
  const { t } = useTranslation('admin');
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
      <h2 className={page.pageTitle}>{t('lookup_title')}</h2>
      <div className={styles.grid}>
        <div>
          <h3 className={styles.blockTitle}>{t('ride_label')}</h3>
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
              {t('fetch')}
            </button>
          </div>
        </div>
        <div>
          <h3 className={styles.blockTitle}>{t('booking_label')}</h3>
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
              {t('fetch')}
            </button>
          </div>
        </div>
      </div>
      <h3 className={styles.resultTitle}>{t('result')}</h3>
      {isIdle && <p className={page.muted}>{t('lookup_idle')}</p>}
      {isLoading && <p className={page.muted}>{t('loading_short')}</p>}
      {isError && <p className={page.error}>{t('lookup_error')}</p>}
      {!isIdle && !isLoading && !isError && (
        <pre className={page.preJson}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}
