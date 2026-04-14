import type { PassengerBookingItem } from './myBookings.types';
import HistorySection from '../../components/HistorySection/HistorySection';
import PassengerBookingCard, {
  type PassengerBookingCardHandlers,
} from './PassengerBookingCard';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface PassengerBookingsTabProps {
  loading: boolean;
  items: PassengerBookingItem[];
  myGroups: MyGroup[];
  sharingLocationBookingId: string | null;
  onSharingChange: (id: string | null) => void;
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
  onSharingChange,
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

  const handlers: PassengerBookingCardHandlers = {
    onSharingChange,
    onTrackDriver: setTrackDriverBookingId,
    onCancelBooking: setBookingToCancel,
    onOpenChat,
  };

  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>טוען...</p>
      ) : items.length === 0 ? (
        <p className={styles.emptyText}>אין הזמנות כנוסע. חפש טרמפ ובקש להצטרף.</p>
      ) : (
        <>
          {activeItems.map((item) => (
            <PassengerBookingCard
              key={item.bookingId}
              item={item}
              myGroups={myGroups}
              sharingLocationBookingId={sharingLocationBookingId}
              cancelling={cancelling}
              chatLoading={chatLoading}
              handlers={handlers}
            />
          ))}
          {pastItems.length > 0 ? (
            <HistorySection title="היסטוריית הזמנות נוסע">
              {pastItems.map((item) => (
                <PassengerBookingCard
                  key={item.bookingId}
                  item={item}
                  myGroups={myGroups}
                  sharingLocationBookingId={sharingLocationBookingId}
                  cancelling={cancelling}
                  chatLoading={chatLoading}
                  handlers={handlers}
                />
              ))}
            </HistorySection>
          ) : null}
        </>
      )}
    </div>
  );
}
