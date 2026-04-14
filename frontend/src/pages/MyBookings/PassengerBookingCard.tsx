import { formatRideDate } from '../../utils/date';
import { STATUS_LABEL } from './myBookings.constants';
import { canPassengerShare, getSource } from './myBookings.utils';
import type { PassengerBookingItem } from './myBookings.types';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface PassengerBookingCardHandlers {
  onSharingChange: (bookingId: string | null) => void;
  onTrackDriver: (bookingId: string) => void;
  onCancelBooking: (bookingId: string) => void;
  onOpenChat: (bookingId: string) => void;
}

export interface PassengerBookingCardProps {
  item: PassengerBookingItem;
  myGroups: MyGroup[];
  sharingLocationBookingId: string | null;
  cancelling: boolean;
  chatLoading: string | null;
  handlers: PassengerBookingCardHandlers;
}

function bookingStatusPill(status: string): string {
  if (status === 'pending_approval') return styles.statusPillPending;
  if (status === 'confirmed') return styles.statusPillConfirmed;
  return styles.statusPillDone;
}

/** Card UI extracted from the tab so the list stays cheap to read and re-render. */
export default function PassengerBookingCard({
  item,
  myGroups,
  sharingLocationBookingId,
  cancelling,
  chatLoading,
  handlers,
}: PassengerBookingCardProps) {
  const { ride, bookingId, bookingStatus, driverName } = item;
  const cardClass = [
    styles.bookingCard,
    bookingStatus === 'pending_approval'
      ? styles.bookingCardPending
      : bookingStatus === 'confirmed'
        ? styles.bookingCardConfirmed
        : styles.bookingCardCancelled,
  ].join(' ');

  return (
    <div className={cardClass}>
      <div className={styles.bookingCardBody}>
        <div className={styles.cardRoute}>
          <span>{ride.origin_name ?? '?'}</span>
          <span style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>→</span>
          <span>{ride.destination_name ?? '?'}</span>
        </div>
        <div className={styles.cardMeta}>
          <span>{formatRideDate(ride.departure_time)}</span>
          <span className={styles.cardMetaSep} />
          <span className={`${styles.statusPill} ${bookingStatusPill(bookingStatus)}`}>
            {STATUS_LABEL[bookingStatus] ?? bookingStatus}
          </span>
          {ride.group_id ? (
            <>
              <span className={styles.cardMetaSep} />
              <span className={styles.groupTag}>{ride.group_name ?? getSource(ride, myGroups)}</span>
            </>
          ) : null}
        </div>
        {driverName ? (
          <div className={styles.cardDriverRow}>
            נהג: {driverName}
          </div>
        ) : null}
      </div>

      {(bookingStatus === 'pending_approval' || bookingStatus === 'confirmed') && (
        <div className={styles.bookingCardActions}>
          {canPassengerShare(bookingStatus, ride.status) ? (
            <>
              <button
                type="button"
                className={`${styles.btnOutline} ${
                  sharingLocationBookingId === bookingId ? styles.btnAccentGreen : ''
                }`}
                onClick={() =>
                  handlers.onSharingChange(
                    sharingLocationBookingId === bookingId ? null : bookingId
                  )
                }
              >
                {sharingLocationBookingId === bookingId ? 'הפסק שיתוף' : 'שתף מיקום'}
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                onClick={() => handlers.onTrackDriver(bookingId)}
              >
                מפה
              </button>
              <button
                type="button"
                className={styles.btnOutline}
                onClick={() => handlers.onOpenChat(bookingId)}
                disabled={chatLoading === bookingId}
              >
                צ&apos;אט
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                onClick={() => handlers.onCancelBooking(bookingId)}
                disabled={cancelling}
              >
                בטל
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className={styles.btnOutline}
                onClick={() => handlers.onOpenChat(bookingId)}
                disabled={chatLoading === bookingId}
              >
                צ&apos;אט
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                onClick={() => handlers.onCancelBooking(bookingId)}
                disabled={cancelling}
              >
                בטל הזמנה
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
