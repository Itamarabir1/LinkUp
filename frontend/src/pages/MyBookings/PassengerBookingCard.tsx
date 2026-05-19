import { Car } from 'lucide-react';
import { formatRideDate } from '../../utils/date';
import { useTranslation } from 'react-i18next';
import { STATUS_LABEL } from './myBookings.constants';
import { canPassengerShare, getSource } from './myBookings.utils';
import type { PassengerBookingItem } from './myBookings.types';
import RouteArrow from '../../components/RouteArrow/RouteArrow';
import { BookingCardActionBar } from './BookingCardActionBar';
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
  const { t } = useTranslation(['bookings', 'common']);
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
          <RouteArrow />
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
          <span className={styles.driverChip}>
            <Car size={12} aria-hidden />
            {driverName}
          </span>
        ) : null}
      </div>

      {(bookingStatus === 'pending_approval' || bookingStatus === 'confirmed') && (
        <BookingCardActionBar>
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
                {sharingLocationBookingId === bookingId ? t('bookings:stopSharing') : t('bookings:shareLocation')}
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                onClick={() => handlers.onTrackDriver(bookingId)}
              >
                {t('bookings:openMap')}
              </button>
              <button
                type="button"
                className={styles.btnOutline}
                onClick={() => handlers.onOpenChat(bookingId)}
                disabled={chatLoading === bookingId}
              >
                {t('bookings:chat')}
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnCancelSubtle}`}
                onClick={() => handlers.onCancelBooking(bookingId)}
                disabled={cancelling}
              >
                {t('bookings:cancel')}
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
                {t('bookings:chat')}
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnCancelSubtle}`}
                onClick={() => handlers.onCancelBooking(bookingId)}
                disabled={cancelling}
              >
                {t('bookings:cancelBooking')}
              </button>
            </>
          )}
        </BookingCardActionBar>
      )}
    </div>
  );
}
