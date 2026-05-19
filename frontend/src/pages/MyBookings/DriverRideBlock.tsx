import { formatRideDate } from '../../utils/date';
import { useTranslation } from 'react-i18next';
import { canDriverOpenMap, canDriverShare, getSource } from './myBookings.utils';
import type { DriverBookingItem } from './myBookings.types';
import DriverBookingPassengerRow from './DriverBookingPassengerRow';
import { BookingCardActionBar } from './BookingCardActionBar';
import RouteArrow from '../../components/RouteArrow/RouteArrow';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface DriverRideBlockHandlers {
  onSharingToggle: (rideId: string) => void;
  onShareStart: (rideId: string) => void | Promise<void>;
  onShareStop: (rideId: string) => void | Promise<void>;
  onOpenMap: (rideId: string) => void;
  onCancelRide: (rideId: string) => void;
  onOpenChat: (bookingId: string) => void;
  onApprove: (bookingId: string) => void;
  onReject: (bookingId: string) => void;
}

export interface DriverRideBlockProps {
  item: DriverBookingItem;
  myGroups: MyGroup[];
  sharingRideId: string | null;
  actionBookingId: string | null;
  chatLoading: string | null;
  handlers: DriverRideBlockHandlers;
}

function rideStatusClass(status: string): string {
  if (status === 'active') return styles.rideStatusActive;
  if (status === 'cancelled' || status === 'completed') return styles.rideStatusDone;
  return styles.rideStatusOpen;
}

function rideStatusLabel(status: string): string {
  if (status === 'active') return 'rides:status_active';
  if (status === 'completed') return 'rides:status_completed';
  if (status === 'cancelled') return 'rides:status_cancelled';
  return 'bookings:openRide';
}

export default function DriverRideBlock({
  item: { ride, passengers },
  myGroups,
  sharingRideId,
  actionBookingId,
  chatLoading,
  handlers,
}: DriverRideBlockProps) {
  const { t } = useTranslation(['bookings', 'common', 'rides']);
  const pendingCount = passengers.filter((p) => p.status === 'pending_approval').length;
  const confirmedCount = passengers.filter((p) => p.status === 'confirmed').length;

  return (
    <div className={styles.driverBlock}>
      <div className={styles.driverBlockHeader}>
        <div className={styles.driverBlockTopRow}>
          <div className={styles.cardRoute}>
            <span>{ride.origin_name ?? '?'}</span>
            <RouteArrow />
            <span>{ride.destination_name ?? '?'}</span>
          </div>
          <span className={`${styles.rideStatusBadge} ${rideStatusClass(ride.status)}`}>
            {t(rideStatusLabel(ride.status))}
          </span>
        </div>

        <div className={styles.cardMeta}>
          <span>{formatRideDate(ride.departure_time)}</span>
          <span className={styles.cardMetaSep} />
          <span>{t('common:seats', { count: ride.available_seats ?? 0 })}</span>
          <span className={styles.cardMetaSep} />
          {ride.group_id ? (
            <span className={styles.groupTag}>{ride.group_name ?? getSource(ride, myGroups)}</span>
          ) : (
            <span className={styles.groupTagPublic}>{t('common:public')}</span>
          )}
        </div>

        {(pendingCount > 0 || confirmedCount > 0) && (
          <div className={styles.driverBlockCounts}>
            {pendingCount > 0 && (
              <span className={`${styles.countBadge} ${styles.countBadgePending}`}>
                {t('bookings:requestsCount', { count: pendingCount })}
              </span>
            )}
            {confirmedCount > 0 && (
              <span className={`${styles.countBadge} ${styles.countBadgeConfirmed}`}>
                {t('bookings:approvedCount', { count: confirmedCount })}
              </span>
            )}
          </div>
        )}
      </div>

      <ul className={styles.passengerList}>
        {passengers.map((passenger) => (
          <DriverBookingPassengerRow
            key={passenger.bookingId}
            passenger={passenger}
            chatLoading={chatLoading}
            actionBookingId={actionBookingId}
            onOpenChat={handlers.onOpenChat}
            onApprove={handlers.onApprove}
            onReject={handlers.onReject}
          />
        ))}
      </ul>

      <BookingCardActionBar>
        {canDriverShare(confirmedCount) && (
          <>
            <button
              type="button"
              className={`${styles.btnOutline} ${
                sharingRideId === ride.ride_id ? styles.btnAccentBlueActive : ''
              }`}
              onClick={() => handlers.onSharingToggle(ride.ride_id)}
            >
              {sharingRideId === ride.ride_id ? t('bookings:stopSharing') : t('bookings:shareLocation')}
            </button>
            {ride.status === 'active' ? (
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                onClick={() => void handlers.onShareStop(ride.ride_id)}
              >
                {t('bookings:endRide')}
              </button>
            ) : (
              <button
                type="button"
                className={styles.btnOutline}
                onClick={() => void handlers.onShareStart(ride.ride_id)}
              >
                {t('bookings:startRide')}
              </button>
            )}
            {canDriverOpenMap(confirmedCount) && (
              <button
                type="button"
                className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                onClick={() => handlers.onOpenMap(ride.ride_id)}
              >
                {t('bookings:openMap')}
              </button>
            )}
          </>
        )}
        <button
          type="button"
          className={`${styles.btnOutline} ${styles.btnCancelSubtle}`}
          onClick={() => handlers.onCancelRide(ride.ride_id)}
        >
          {t('rides:cancelRide')}
        </button>
      </BookingCardActionBar>
    </div>
  );
}
