import type { Ride, DriverInfo } from '../../types/api';
import { formatDateTimeNoSeconds } from '../../utils/date';
import ErrorBanner from '../../components/ErrorBanner';
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
  return (
    <div className={styles.card}>
      <div className={styles.cardRoute}>
        {r.origin_name ?? '?'} ← {r.destination_name ?? '?'}
      </div>
      <div className={styles.cardMeta}>
        {formatDateTimeNoSeconds(r.departure_time)} · {r.available_seats} מושבים
      </div>
      {r.route_summary && (
        <div className={`${styles.cardMeta} ${styles.cardRouteSummary}`}>
          כביש מרכזי: {r.route_summary}
        </div>
      )}
      <div className={styles.cardActions}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnOutline}`}
          onClick={() => onFetchDriver(r.ride_id)}
          disabled={loadingDriverRideId === r.ride_id}
        >
          {loadingDriverRideId === r.ride_id ? '...' : 'הצג פרטי הנהג'}
        </button>
        {r.user_booking_status === 'pending_approval' ? (
          <span className={styles.statusPending}>⏳ ממתין לאישור</span>
        ) : r.user_booking_status === 'confirmed' ? (
          <span className={styles.statusConfirmed}>✅ מאושר</span>
        ) : (
          <button
            type="button"
            className={`${styles.btn} ${styles.btnSuccess}`}
            onClick={() => onRequestJoin(r)}
            disabled={sendingRequestRideId !== null || requestSuccessRideId === r.ride_id}
          >
            {requestSuccessRideId === r.ride_id
              ? 'הבקשה נשלחה'
              : sendingRequestRideId === r.ride_id
                ? 'מעבד...'
                : 'בקש להצטרפות לנסיעה'}
          </button>
        )}
      </div>
      {requestErrorRideId === r.ride_id && requestErrorMessage ? (
        <ErrorBanner
          message={requestErrorMessage}
          variant="compact"
          className={`${styles.pageError} ${styles.requestErrorBanner}`.trim()}
          role="status"
        />
      ) : null}
      {driverInfo && (
        <div className={`${styles.cardMeta} ${styles.driverInfoBox}`}>
          <strong>נהג:</strong> {driverInfo.full_name}
          {driverInfo.phone_number && (
            <>
              {' '}
              · <a href={`tel:${driverInfo.phone_number}`}>{driverInfo.phone_number}</a>
            </>
          )}
        </div>
      )}
    </div>
  );
}
