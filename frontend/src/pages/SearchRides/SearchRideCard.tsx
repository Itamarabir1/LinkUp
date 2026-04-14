import type { Ride, DriverInfo } from '../../types/api';
import { formatDateTimeNoSeconds } from '../../utils/date';
import { Clock, CheckCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import styles from './SearchRides.module.css';

type Props = {
  ride: Ride;
  driverInfo?: DriverInfo;
  loadingDriverRideId: string | null;
  sendingRequestRideId: string | null;
  requestSuccessRideId: string | null;
  requestErrorRideId: string | null;
  requestErrorMessage: string;
  onFetchDriver: (rideId: string) => void;
  onRequestJoin: (ride: Ride) => void;
};

export function SearchRideCard({
  ride: r,
  driverInfo,
  loadingDriverRideId,
  sendingRequestRideId,
  requestSuccessRideId,
  requestErrorRideId,
  requestErrorMessage,
  onFetchDriver,
  onRequestJoin,
}: Props) {
  const { t } = useTranslation('rides');
  return (
    <div className={styles.card}>
      <div className={styles.cardRoute}>
        <span>{r.origin_name ?? '?'}</span>
        <span style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>→</span>
        <span>{r.destination_name ?? '?'}</span>
      </div>

      <div className={styles.cardMeta}>
        <span>{formatDateTimeNoSeconds(r.departure_time)}</span>
        <span className={styles.cardMetaSep} />
        <span className={styles.seatsBadge}>{t('common:seats', { count: r.available_seats ?? 0 })}</span>
        {r.route_summary && (
          <>
            <span className={styles.cardMetaSep} />
            <span>{r.route_summary}</span>
          </>
        )}
      </div>

      <div className={styles.cardActions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnOutline}`}
          onClick={() => onFetchDriver(r.ride_id)}
          disabled={loadingDriverRideId === r.ride_id}
        >
          {loadingDriverRideId === r.ride_id ? '...' : t('driverDetails')}
        </button>

        {r.user_booking_status === 'pending_approval' ? (
          <span className={styles.statusPending}>
            <Clock size={12} style={{ display: 'inline', marginLeft: 4 }} />
            {t('pendingApproval')}
          </span>
        ) : r.user_booking_status === 'confirmed' ? (
          <span className={styles.statusConfirmed}>
            <CheckCircle size={12} style={{ display: 'inline', marginLeft: 4 }} />
            {t('approved')}
          </span>
        ) : (
          <button
            type="button"
            className={`${styles.btn} ${styles.btnSuccess}`}
            onClick={() => onRequestJoin(r)}
            disabled={sendingRequestRideId !== null || requestSuccessRideId === r.ride_id}
          >
            {requestSuccessRideId === r.ride_id
              ? `✓ ${t('requestSent')}`
              : sendingRequestRideId === r.ride_id
              ? t('common:sending')
              : t('requestToJoin')}
          </button>
        )}
      </div>

      {requestErrorRideId === r.ride_id && requestErrorMessage ? (
        <div className={`${styles.pageError} ${styles.requestErrorBanner}`}>
          {requestErrorMessage}
        </div>
      ) : null}

      {driverInfo && (
        <div className={styles.driverInfoBox}>
          <strong>{t('driverLabel')}</strong> {driverInfo.full_name}
          {driverInfo.phone_number && (
            <> · <a href={`tel:${driverInfo.phone_number}`}>{driverInfo.phone_number}</a></>
          )}
        </div>
      )}
    </div>
  );
}
