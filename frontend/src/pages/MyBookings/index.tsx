import ConfirmModal from '../../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../../components/ErrorBanner';
import LiveMapModal from '../../components/LiveMapModal';
import LiveRideMapModal from '../../components/LiveRideMapModal';
import DriverBookingsTab from './DriverBookingsTab';
import PassengerBookingsTab from './PassengerBookingsTab';
import { useMyBookings } from './useMyBookings';
import styles from './MyBookings.module.css';

export default function MyBookings() {
  const vm = useMyBookings();

  return (
    <div className={styles.page}>
      <div role="tablist" className={styles.pageTabs}>
        <button
          type="button"
          role="tab"
          aria-selected={vm.activeTab === 'passenger'}
          className={vm.activeTab === 'passenger' ? styles.tabActive : styles.tab}
          onClick={() => vm.setActiveTab('passenger')}
        >
          אני נוסע
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vm.activeTab === 'driver'}
          className={vm.activeTab === 'driver' ? styles.tabActive : styles.tab}
          onClick={() => vm.setActiveTab('driver')}
        >
          אני נהג
        </button>
      </div>

      {vm.error ? <ErrorBanner message={vm.error} className={styles.pageError} /> : null}

      {vm.activeTab === 'passenger' && (
        <PassengerBookingsTab
          loading={vm.passengerLoading}
          items={vm.passengerList}
          myGroups={vm.myGroups}
          sharingLocationBookingId={vm.sharingLocationBookingId}
          setSharingLocationBookingId={vm.setSharingLocationBookingId}
          setTrackDriverBookingId={vm.setTrackDriverBookingId}
          setBookingToCancel={vm.setBookingToCancel}
          cancelling={vm.cancelling}
          chatLoading={vm.chatLoading}
          onOpenChat={vm.handleOpenChat}
        />
      )}

      {vm.activeTab === 'driver' && (
        <DriverBookingsTab
          loading={vm.driverLoading}
          items={vm.driverList}
          myGroups={vm.myGroups}
          sharingRideId={vm.sharingRideId}
          setSharingRideId={vm.setSharingRideId}
          setLiveRideId={vm.setLiveRideId}
          setRideToCancel={vm.setRideToCancel}
          chatLoading={vm.chatLoading}
          actionBookingId={vm.actionBookingId}
          onShareStart={vm.handleShareStart}
          onShareStop={vm.handleShareStop}
          onOpenChat={vm.handleOpenChat}
          onApprove={vm.handleApprove}
          onReject={vm.handleReject}
        />
      )}

      <ConfirmModal
        open={vm.bookingToCancel != null}
        onClose={() => vm.setBookingToCancel(null)}
        title="האם אתה בטוח שאתה רוצה לבטל את ההזמנה הזו?"
        confirmLabel="אישור"
        variant="danger"
        loading={vm.cancelling}
        onConfirm={vm.confirmCancelBooking}
        titleId="confirm-cancel-booking-title"
      />

      <ConfirmModal
        open={vm.rideToCancel != null}
        onClose={() => vm.setRideToCancel(null)}
        title="האם אתה בטוח שאתה רוצה לבטל את הנסיעה?"
        confirmLabel="אישור"
        variant="danger"
        loading={vm.cancellingRide}
        onConfirm={vm.confirmCancelRide}
        titleId="confirm-cancel-ride-mybookings"
      />

      {vm.trackDriverBookingId && (
        <LiveMapModal
          bookingId={vm.trackDriverBookingId}
          onClose={() => vm.setTrackDriverBookingId(null)}
        />
      )}

      {vm.liveRideId && vm.user && (
        <LiveRideMapModal
          rideId={vm.liveRideId}
          driverId={vm.user.user_id}
          broadcastToServer={false}
          onClose={() => vm.setLiveRideId(null)}
        />
      )}
    </div>
  );
}
