import { MapPin, MessageCircle, Navigation } from 'lucide-react';
import { formatRideDate } from '../../utils/date';
import { STATUS_LABEL } from './myBookings.constants';
import { canPassengerShare, getSource } from './myBookings.utils';
import type { PassengerBookingItem } from './myBookings.types';
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
  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>טוען...</p>
      ) : items.length === 0 ? (
        <p className={styles.emptyText}>אין הזמנות כנוסע. חפש טרמפ ובקש להצטרף.</p>
      ) : (
        items.map(({ ride, bookingId, bookingStatus, driverName }) => (
          <div key={bookingId} className={styles.bookingCard}>
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
        ))
      )}
    </div>
  );
}
