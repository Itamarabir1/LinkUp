import type { DriverBookingItem } from './myBookings.types';
import { useTranslation } from 'react-i18next';
import DriverRideBlock, { type DriverRideBlockHandlers } from './DriverRideBlock';
import HistorySection from '../../components/HistorySection/HistorySection';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface DriverBookingsTabProps {
  loading: boolean;
  items: DriverBookingItem[];
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
}

export default function DriverBookingsTab({
  loading,
  items,
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
}: DriverBookingsTabProps) {
  const { t } = useTranslation(['bookings', 'common']);
  const activeItems = items.filter(
    (item) => item.ride.status !== 'cancelled' && item.ride.status !== 'completed'
  );
  const pastItems = items.filter(
    (item) => item.ride.status === 'cancelled' || item.ride.status === 'completed'
  );

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

  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>{t('common:loading')}</p>
      ) : items.length === 0 ? (
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
          {pastItems.length > 0 ? (
            <HistorySection title={t('bookings:driverHistoryTitle')}>
              {pastItems.map((item) => (
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
            </HistorySection>
          ) : null}
        </>
      )}
    </div>
  );
}
