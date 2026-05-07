import type { PassengerBookingItem } from './myBookings.types';
import { useTranslation } from 'react-i18next';
import HistorySection from '../../components/HistorySection/HistorySection';
import PassengerBookingCard, {
  type PassengerBookingCardHandlers,
} from './PassengerBookingCard';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface PassengerBookingsTabProps {
  loading: boolean;
  activeItems: PassengerBookingItem[];
  historyItems: PassengerBookingItem[];
  myGroups: MyGroup[];
  sharingLocationBookingId: string | null;
  onSharingChange: (id: string | null) => void;
  setTrackDriverBookingId: (id: string) => void;
  setBookingToCancel: (id: string) => void;
  cancelling: boolean;
  chatLoading: string | null;
  onOpenChat: (bookingId: string) => void;
  onLoadMoreHistory?: () => void;
  hasMoreHistory?: boolean;
  loadingMoreHistory?: boolean;
}

export default function PassengerBookingsTab({
  loading,
  activeItems,
  historyItems,
  myGroups,
  sharingLocationBookingId,
  onSharingChange,
  setTrackDriverBookingId,
  setBookingToCancel,
  cancelling,
  chatLoading,
  onOpenChat,
  onLoadMoreHistory,
  hasMoreHistory = false,
  loadingMoreHistory = false,
}: PassengerBookingsTabProps) {
  const { t } = useTranslation(['bookings', 'common']);

  const handlers: PassengerBookingCardHandlers = {
    onSharingChange,
    onTrackDriver: setTrackDriverBookingId,
    onCancelBooking: setBookingToCancel,
    onOpenChat,
  };

  const isEmpty =
    !loading && activeItems.length === 0 && historyItems.length === 0 && !hasMoreHistory;

  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>{t('common:loading')}</p>
      ) : isEmpty ? (
        <p className={styles.emptyText}>{t('bookings:noPassengerBookings')}</p>
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
          {(historyItems.length > 0 || hasMoreHistory) && (
            <HistorySection title={t('bookings:passengerHistoryTitle')}>
              {historyItems.map((item) => (
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
              {hasMoreHistory && onLoadMoreHistory ? (
                <div className={styles.historyLoadMore}>
                  <button
                    type="button"
                    className={styles.historyLoadMoreBtn}
                    disabled={loadingMoreHistory}
                    onClick={() => onLoadMoreHistory()}
                  >
                    {loadingMoreHistory ? t('common:loading') : t('bookings:loadMoreHistory')}
                  </button>
                </div>
              ) : null}
            </HistorySection>
          )}
        </>
      )}
    </div>
  );
}
