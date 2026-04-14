import { MessageCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['bookings', 'common']);
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
          {t('common:seats', { count: passenger.numSeats })}
          {passenger.pickupName ? ` · ${t('bookings:pickup')}: ${passenger.pickupName}` : ''}
          {passenger.dropoffName ? ` · ${t('bookings:dropoff')}: ${passenger.dropoffName}` : ''}
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
              ✅ {t('bookings:approve')}
            </button>
            <button
              type="button"
              className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
              onClick={() => onReject(passenger.bookingId)}
              disabled={actionBookingId === passenger.bookingId}
            >
              ❌ {t('bookings:reject')}
            </button>
            <button
              type="button"
              className={styles.btnOutline}
              onClick={() => onOpenChat(passenger.bookingId)}
              disabled={chatLoading === passenger.bookingId}
            >
              <MessageCircle size={15} />
              {t('bookings:chat')}
            </button>
          </div>
        )}
        {passenger.status === 'confirmed' && (
          <>
            <span className={styles.statusConfirmed}>{t('bookings:bookingStatus_approved')}</span>
            <button
              type="button"
              className={styles.btnOutline}
              onClick={() => onOpenChat(passenger.bookingId)}
              disabled={chatLoading === passenger.bookingId}
            >
              <MessageCircle size={15} />
              {t('bookings:chat')}
            </button>
          </>
        )}
        {passenger.status === 'rejected' && <span className={styles.statusRejected}>{t('bookings:bookingStatus_rejected')}</span>}
      </div>
    </li>
  );
}
