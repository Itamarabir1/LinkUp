import { formatRideDate } from '../../utils/date';
import { canDriverOpenMap, canDriverShare, getSource } from './myBookings.utils';
import type { DriverBookingItem } from './myBookings.types';
import DriverBookingPassengerRow from './DriverBookingPassengerRow';
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
  if (status === 'active') return 'פעילה';
  if (status === 'completed') return 'הושלמה';
  if (status === 'cancelled') return 'בוטלה';
  return 'פתוחה';
}

export default function DriverRideBlock({
  item: { ride, passengers },
  myGroups,
  sharingRideId,
  actionBookingId,
  chatLoading,
  handlers,
}: DriverRideBlockProps) {
  const pendingCount = passengers.filter((p) => p.status === 'pending_approval').length;
  const confirmedCount = passengers.filter((p) => p.status === 'confirmed').length;

  return (
    <div className={styles.driverBlock}>
      <div className={styles.driverBlockHeader}>
        <div className={styles.driverBlockLeft}>
          <div className={styles.cardRoute}>
            <span>{ride.origin_name ?? '?'}</span>
            <span style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>→</span>
            <span>{ride.destination_name ?? '?'}</span>
          </div>
          <div className={styles.cardMeta}>
            <span>{formatRideDate(ride.departure_time)}</span>
            <span className={styles.cardMetaSep} />
            <span>{ride.available_seats} מושבים פנויים</span>
          </div>
          <div className={styles.driverBlockCounts}>
            {pendingCount > 0 && (
              <span className={`${styles.countBadge} ${styles.countBadgePending}`}>
                {pendingCount} בקשות
              </span>
            )}
            {confirmedCount > 0 && (
              <span className={`${styles.countBadge} ${styles.countBadgeConfirmed}`}>
                {confirmedCount} מאושרים
              </span>
            )}
          </div>
          <div className={styles.driverBlockTagWrap}>
            {ride.group_id ? (
              <span className={styles.groupTag}>{ride.group_name ?? getSource(ride, myGroups)}</span>
            ) : (
              <span className={styles.groupTagPublic}>ציבורי</span>
            )}
          </div>
        </div>

        <div className={styles.driverBlockRight}>
          <span className={`${styles.rideStatusBadge} ${rideStatusClass(ride.status)}`}>
            {rideStatusLabel(ride.status)}
          </span>
          <div className={styles.driverBlockActionRow}>
            {canDriverShare(confirmedCount) && (
              <>
                <button
                  type="button"
                  className={`${styles.btnOutline} ${
                    sharingRideId === ride.ride_id ? styles.btnAccentBlueActive : ''
                  }`}
                  onClick={() => handlers.onSharingToggle(ride.ride_id)}
                >
                  {sharingRideId === ride.ride_id ? 'הפסק שיתוף' : 'שתף מיקום'}
                </button>
                {ride.status === 'active' ? (
                  <button
                    type="button"
                    className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                    onClick={() => void handlers.onShareStop(ride.ride_id)}
                  >
                    סיים נסיעה
                  </button>
                ) : (
                  <button
                    type="button"
                    className={styles.btnOutline}
                    onClick={() => void handlers.onShareStart(ride.ride_id)}
                  >
                    התחל נסיעה
                  </button>
                )}
                {canDriverOpenMap(confirmedCount) && (
                  <button
                    type="button"
                    className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                    onClick={() => handlers.onOpenMap(ride.ride_id)}
                  >
                    מפה
                  </button>
                )}
              </>
            )}
            <button
              type="button"
              className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
              onClick={() => handlers.onCancelRide(ride.ride_id)}
            >
              בטל נסיעה
            </button>
          </div>
        </div>
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
    </div>
  );
}
