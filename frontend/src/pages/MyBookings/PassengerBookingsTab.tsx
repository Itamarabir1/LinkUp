import { MapPin, MessageCircle, Navigation } from 'lucide-react';
import { formatRideDate } from '../../utils/date';
import { STATUS_LABEL } from './myBookings.constants';
import { canPassengerShare, getSource } from './myBookings.utils';
import type { PassengerBookingItem } from './myBookings.types';
import HistorySection from '../../components/HistorySection/HistorySection';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface PassengerBookingsTabProps {
  loading: boolean;
  items: PassengerBookingItem[];
  myGroups: MyGroup[];
  sharingLocationBookingId: string | null;
  setSharingLocationBookingId: React.Dispatch<React.SetStateAction<string | null>>;
  setTrackDriverBookingId: (id: string) => void;
  setBookingToCancel: (id: string) => void;
  cancelling: boolean;
  chatLoading: string | null;
  onOpenChat: (bookingId: string) => void;
}

export default function PassengerBookingsTab({
  loading,
  items,
  myGroups,
  sharingLocationBookingId,
  setSharingLocationBookingId,
  setTrackDriverBookingId,
  setBookingToCancel,
  cancelling,
  chatLoading,
  onOpenChat,
}: PassengerBookingsTabProps) {
  const activeItems = items.filter(
    (item) => item.bookingStatus !== 'cancelled' && item.bookingStatus !== 'completed'
  );
  const pastItems = items.filter(
    (item) => item.bookingStatus === 'cancelled' || item.bookingStatus === 'completed'
  );

  const renderItem = ({ ride, bookingId, bookingStatus, driverName }: PassengerBookingItem) => {
    const cardClass = [
      styles.bookingCard,
      bookingStatus === 'pending_approval' ? styles.bookingCardPending :
      bookingStatus === 'confirmed' ? styles.bookingCardConfirmed :
      styles.bookingCardCancelled
    ].join(' ');

    return (
    <div key={bookingId} className={cardClass}>
      <div className={styles.cardRoute}>
        {ride.origin_name ?? '?'} ← {ride.destination_name ?? '?'}
      </div>
      <div className={styles.cardMeta}>
        {formatRideDate(ride.departure_time)} · {STATUS_LABEL[bookingStatus] ?? bookingStatus}
      </div>
      {driverName && <div className={styles.cardMeta}>נהג: {driverName}</div>}
      <div className={styles.cardMeta}>{getSource(ride, myGroups)}</div>
      {(ride.group_name ?? (ride.group_id ? getSource(ride, myGroups) : null)) && (
        <div className={styles.cardTagWrap}>
          <span className={styles.groupTag}>{ride.group_name ?? getSource(ride, myGroups)}</span>
        </div>
      )}
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
                  setSharingLocationBookingId((prev) => (prev === bookingId ? null : bookingId))
                }
              >
                <Navigation size={15} />
                {sharingLocationBookingId === bookingId ? 'הפסק שיתוף' : 'שתף מיקום'}
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                onClick={() => setTrackDriverBookingId(bookingId)}
              >
                <MapPin size={15} /> מפה
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                onClick={() => setBookingToCancel(bookingId)}
                disabled={cancelling}
              >
                בטל
              </button>
              <button
                type="button"
                className={styles.btnOutline}
                onClick={() => onOpenChat(bookingId)}
                disabled={chatLoading === bookingId}
              >
                <MessageCircle size={15} />
                צ&apos;אט
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className={styles.btnOutline}
                onClick={() => onOpenChat(bookingId)}
                disabled={chatLoading === bookingId}
              >
                <MessageCircle size={15} />
                צ&apos;אט
              </button>
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                onClick={() => setBookingToCancel(bookingId)}
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
  };

  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>טוען...</p>
      ) : items.length === 0 ? (
        <p className={styles.emptyText}>אין הזמנות כנוסע. חפש טרמפ ובקש להצטרף.</p>
      ) : (
        <>
          {activeItems.map(renderItem)}
          {pastItems.length > 0 ? (
            <HistorySection title="היסטוריית הזמנות נוסע">
              {pastItems.map(renderItem)}
            </HistorySection>
          ) : null}
        </>
      )}
    </div>
  );
}
