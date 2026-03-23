import { MapPin, Navigation } from 'lucide-react';
import { formatRideDate } from '../../utils/date';
import { canDriverOpenMap, canDriverShare, getSource } from './myBookings.utils';
import type { DriverBookingItem } from './myBookings.types';
import DriverBookingPassengerRow from './DriverBookingPassengerRow';
import styles from './MyBookings.module.css';

type MyGroup = { group_id: string; name: string };

export interface DriverRideBlockProps {
  item: DriverBookingItem;
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

export default function DriverRideBlock({
  item: { ride, passengers },
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
}: DriverRideBlockProps) {
  const pendingCount = passengers.filter((p) => p.status === 'pending_approval').length;
  const confirmedCount = passengers.filter((p) => p.status === 'confirmed').length;

  return (
    <div className={styles.driverBlock}>
      <div className={styles.driverBlockHeader}>
        <div className={styles.cardRoute}>
          {ride.origin_name ?? '?'} ← {ride.destination_name ?? '?'}
        </div>
        <div className={styles.cardMeta}>
          {formatRideDate(ride.departure_time)} · {ride.available_seats} מושבים פנויים
        </div>
        <div className={styles.driverBlockCounts}>
          {pendingCount > 0 && <span>{pendingCount} בקשות</span>}
          {confirmedCount > 0 && (
            <span className={pendingCount > 0 ? styles.countSep : ''}>{confirmedCount} מאושרים</span>
          )}
        </div>
        <div className={styles.driverBlockTagWrap}>
          {ride.group_name ?? (ride.group_id ? getSource(ride, myGroups) : null) ? (
            <span className={styles.groupTag}>{ride.group_name ?? getSource(ride, myGroups)}</span>
          ) : (
            <span className={styles.groupTagPublic}>ציבורי</span>
          )}
        </div>
        <div className={styles.driverBlockActions}>
          {canDriverShare(confirmedCount) && (
            <>
              <button
                type="button"
                className={`${styles.btnOutline} ${
                  sharingRideId === ride.ride_id ? styles.btnAccentBlueActive : ''
                }`}
                onClick={() => setSharingRideId((prev) => (prev === ride.ride_id ? null : ride.ride_id))}
              >
                <Navigation size={15} />
                {sharingRideId === ride.ride_id ? 'הפסק שיתוף' : 'שתף מיקום'}
              </button>
              {ride.status === 'active' ? (
                <button
                  type="button"
                  className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
                  onClick={() => void onShareStop(ride.ride_id)}
                >
                  ■ סיים נסיעה
                </button>
              ) : (
                <button
                  type="button"
                  className={styles.btnOutline}
                  onClick={() => void onShareStart(ride.ride_id)}
                >
                  ▶ התחל נסיעה
                </button>
              )}
              {canDriverOpenMap(confirmedCount) && (
                <button
                  type="button"
                  className={`${styles.btnOutline} ${styles.btnAccentBlue}`}
                  onClick={() => setLiveRideId(ride.ride_id)}
                >
                  <MapPin size={15} /> מפה
                </button>
              )}
            </>
          )}
          <button
            type="button"
            className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
            onClick={() => setRideToCancel(ride.ride_id)}
          >
            בטל נסיעה
          </button>
        </div>
      </div>
      <ul className={styles.passengerList}>
        {passengers.map((passenger) => (
          <DriverBookingPassengerRow
            key={passenger.bookingId}
            passenger={passenger}
            chatLoading={chatLoading}
            actionBookingId={actionBookingId}
            onOpenChat={onOpenChat}
            onApprove={onApprove}
            onReject={onReject}
          />
        ))}
      </ul>
    </div>
  );
}
