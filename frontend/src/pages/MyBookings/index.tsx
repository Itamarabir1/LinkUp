import ConfirmModal from '../../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../../components/ErrorBanner';
import LiveMapModal from '../../components/LiveMapModal';
import LiveRideMapModal from '../../components/LiveRideMapModal';
import { useTranslation } from 'react-i18next';
import DriverBookingsTab from './DriverBookingsTab';
import PassengerBookingsTab from './PassengerBookingsTab';
import { useMyBookings } from './useMyBookings';
import styles from './MyBookings.module.css';

export default function MyBookings() {
  const { t } = useTranslation(['bookings', 'common']);
  const vm = useMyBookings();

  return (
    <div className={styles.page}>
      <div className={styles.tabWrap}>
        <div role="tablist" className={styles.tabPills}>
          <button
            type="button"
            role="tab"
            aria-selected={vm.activeTab === 'passenger'}
            className={
              vm.activeTab === 'passenger'
                ? `${styles.tabPill} ${styles.tabPillActive}`
                : styles.tabPill
            }
            onClick={() => vm.setActiveTab('passenger')}
          >
            {t('bookings:iAmPassenger')}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={vm.activeTab === 'driver'}
            className={
              vm.activeTab === 'driver' ? `${styles.tabPill} ${styles.tabPillActive}` : styles.tabPill
            }
            onClick={() => vm.setActiveTab('driver')}
          >
            {t('bookings:iAmDriver')}
          </button>
        </div>
      </div>

      {vm.error ? <ErrorBanner message={vm.error} className={styles.pageError} /> : null}

      <div className={styles.content}>
        {vm.activeTab === 'passenger' && (
          <PassengerBookingsTab
            loading={vm.passenger.loading}
            items={vm.passenger.list}
            myGroups={vm.myGroups}
            sharingLocationBookingId={vm.passenger.sharingLocationBookingId}
            onSharingChange={(id) => vm.passenger.setSharingLocationBookingId(id)}
            setTrackDriverBookingId={vm.passenger.setTrackDriverBookingId}
            setBookingToCancel={vm.passenger.setBookingToCancel}
            cancelling={vm.passenger.cancelling}
            chatLoading={vm.chat.loading}
            onOpenChat={vm.chat.onOpen}
          />
        )}

        {vm.activeTab === 'driver' && (
          <DriverBookingsTab
            loading={vm.driver.loading}
            items={vm.driver.list}
            myGroups={vm.myGroups}
            sharingRideId={vm.driver.sharingRideId}
            setSharingRideId={vm.driver.setSharingRideId}
            setLiveRideId={vm.driver.setLiveRideId}
            setRideToCancel={vm.driver.setRideToCancel}
            chatLoading={vm.chat.loading}
            actionBookingId={vm.driver.actionBookingId}
            onShareStart={vm.driver.handleShareStart}
            onShareStop={vm.driver.handleShareStop}
            onOpenChat={vm.chat.onOpen}
            onApprove={vm.driver.handleApprove}
            onReject={vm.driver.handleReject}
          />
        )}
      </div>

      <ConfirmModal
        open={vm.passenger.bookingToCancel != null}
        onClose={() => vm.passenger.setBookingToCancel(null)}
        title={t('bookings:confirmCancelBooking')}
        confirmLabel={t('common:confirm')}
        variant="danger"
        loading={vm.passenger.cancelling}
        onConfirm={vm.passenger.confirmCancelBooking}
        titleId="confirm-cancel-booking-title"
      />

      <ConfirmModal
        open={vm.driver.rideToCancel != null}
        onClose={() => vm.driver.setRideToCancel(null)}
        title={t('bookings:confirmCancelRide')}
        confirmLabel={t('common:confirm')}
        variant="danger"
        loading={vm.driver.cancellingRide}
        onConfirm={vm.driver.confirmCancelRide}
        titleId="confirm-cancel-ride-mybookings"
      />

      {vm.passenger.trackDriverBookingId && (
        <LiveMapModal
          bookingId={vm.passenger.trackDriverBookingId}
          onClose={() => vm.passenger.setTrackDriverBookingId(null)}
        />
      )}

      {vm.driver.liveRideId && vm.user && (
        <LiveRideMapModal
          rideId={vm.driver.liveRideId}
          driverId={vm.user.user_id}
          broadcastToServer={false}
          onClose={() => vm.driver.setLiveRideId(null)}
        />
      )}
    </div>
  );
}
