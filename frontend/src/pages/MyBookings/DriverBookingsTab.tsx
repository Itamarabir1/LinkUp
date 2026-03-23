import type { DriverBookingItem } from './myBookings.types';
import DriverRideBlock from './DriverRideBlock';
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

export default function DriverBookingsTab(props: DriverBookingsTabProps) {
  const { loading, items, myGroups, ...blockProps } = props;

  return (
    <div className={styles.cardList}>
      {loading ? (
        <p className={styles.pageLoading}>טוען...</p>
      ) : items.length === 0 ? (
        <p className={styles.emptyText}>אין הזמנות שאישרת. נוסעים שאישרת יופיעו כאן.</p>
      ) : (
        items.map((item) => (
          <DriverRideBlock key={item.ride.ride_id} item={item} myGroups={myGroups} {...blockProps} />
        ))
      )}
    </div>
  );
}
