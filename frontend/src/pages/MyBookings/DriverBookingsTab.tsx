import type { DriverBookingItem } from './myBookings.types';
import { useTranslation } from 'react-i18next';
import DriverRideBlock, { type DriverRideBlockHandlers } from './DriverRideBlock';
import HistorySection from '../../components/HistorySection/HistorySection';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface DriverBookingsTabProps {
  loading: boolean;
  activeItems: DriverBookingItem[];
  historyItems: DriverBookingItem[];
  myGroups: MyGroup[];
  sharingRideId: string | null;
  setSharingRideId: React.Dispatch<React.SetStateAction<string | null>>;
  setLiveRideId: (rideId: string) => void;
  setRideToCancel: (rideId: string) => void;
  chatLoading: string | null;
  actionBookingId: string | null;
  onShareStart: (rideId: string) => void | Promise<void>;
  onShareStop: (rideId: string) => void | Promise<void>;
  onOpenChat: (bookingId: string) => void;
  onApprove: (bookingId: string) => void;
  onReject: (bookingId: string) => void;
  onLoadMoreHistory?: () => void;
  hasMoreHistory?: boolean;
  loadingMoreHistory?: boolean;
}

export default function DriverBookingsTab({
  loading,
  activeItems,
  historyItems,
  myGroups,
  sharingRideId,
  setSharingRideId,
  setLiveRideId,
  setRideToCancel,
  chatLoading,
  actionBookingId,
  onShareStart,
  onShareStop,
  onOpenChat,
  onApprove,
  onReject,
  onLoadMoreHistory,
  hasMoreHistory = false,
  loadingMoreHistory = false,
}: DriverBookingsTabProps) {
  const { t } = useTranslation(['bookings', 'common']);
  const handlers: DriverRideBlockHandlers = {
    onSharingToggle: (rideId) => setSharingRideId((prev) => (prev === rideId ? null : rideId)),
    onShareStart,
    onShareStop,
    onOpenMap: setLiveRideId,
    onCancelRide: setRideToCancel,
    onOpenChat,
    onApprove,
    onReject,
  };

  const isEmpty =
    !loading && activeItems.length === 0 && historyItems.length === 0 && !hasMoreHistory;

  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>{t('common:loading')}</p>
      ) : isEmpty ? (
        <p className={styles.emptyText}>{t('bookings:noDriverBookings')}</p>
      ) : (
        <>
          {activeItems.map((item) => (
            <DriverRideBlock
              key={item.ride.ride_id}
              item={item}
              myGroups={myGroups}
              sharingRideId={sharingRideId}
              actionBookingId={actionBookingId}
              chatLoading={chatLoading}
              handlers={handlers}
            />
          ))}
          {(historyItems.length > 0 || hasMoreHistory) && (
            <HistorySection title={t('bookings:driverHistoryTitle')}>
              {historyItems.map((item) => (
                <DriverRideBlock
                  key={item.ride.ride_id}
                  item={item}
                  myGroups={myGroups}
                  sharingRideId={sharingRideId}
                  actionBookingId={actionBookingId}
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
