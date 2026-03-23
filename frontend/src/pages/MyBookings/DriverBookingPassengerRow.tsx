import { MessageCircle } from 'lucide-react';
import { AVATAR_COLORS } from './myBookings.constants';
import { avatarInitial } from './myBookings.utils';
import type { PassengerInRide } from './myBookings.types';
import styles from './MyBookings.module.css';

export interface DriverBookingPassengerRowProps {
  passenger: PassengerInRide;
  chatLoading: string | null;
  actionBookingId: string | null;
  onOpenChat: (bookingId: string) => void;
  onApprove: (bookingId: string) => void;
  onReject: (bookingId: string) => void;
}

export default function DriverBookingPassengerRow({
  passenger,
  chatLoading,
  actionBookingId,
  onOpenChat,
  onApprove,
  onReject,
}: DriverBookingPassengerRowProps) {
  return (
    <li className={styles.passengerRow}>
      <div
        className={styles.passengerAvatar}
        style={{
          ['--avatar-bg' as string]:
            AVATAR_COLORS[Math.abs(passenger.passengerName.length) % AVATAR_COLORS.length],
        }}
      >
        {avatarInitial(passenger.passengerName)}
      </div>
      <div className={styles.passengerInfo}>
        <div className={styles.passengerName}>{passenger.passengerName}</div>
        <div className={styles.passengerMeta}>
          {passenger.numSeats} מושבים
          {passenger.pickupName ? ` · עולה: ${passenger.pickupName}` : ''}
          {passenger.dropoffName ? ` · יורד: ${passenger.dropoffName}` : ''}
        </div>
      </div>
      <div className={styles.passengerActions}>
        {passenger.status === 'pending_approval' && (
          <div className={styles.passengerPendingActions}>
            <button
              type="button"
              className={`${styles.btnOutline} ${styles.btnAccentGreen}`}
              onClick={() => onApprove(passenger.bookingId)}
              disabled={actionBookingId === passenger.bookingId}
            >
              ✅ אשר
            </button>
            <button
              type="button"
              className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
              onClick={() => onReject(passenger.bookingId)}
              disabled={actionBookingId === passenger.bookingId}
            >
              ❌ דחה
            </button>
            <button
              type="button"
              className={styles.btnOutline}
              onClick={() => onOpenChat(passenger.bookingId)}
              disabled={chatLoading === passenger.bookingId}
            >
              <MessageCircle size={15} />
              צ&apos;אט
            </button>
          </div>
        )}
        {passenger.status === 'confirmed' && (
          <>
            <span className={styles.statusConfirmed}>מאושר</span>
            <button
              type="button"
              className={styles.btnOutline}
              onClick={() => onOpenChat(passenger.bookingId)}
              disabled={chatLoading === passenger.bookingId}
            >
              <MessageCircle size={15} />
              צ&apos;אט
            </button>
          </>
        )}
        {passenger.status === 'rejected' && <span className={styles.statusRejected}>נדחה</span>}
      </div>
    </li>
  );
}
