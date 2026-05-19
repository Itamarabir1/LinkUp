import { Check, MessageCircle, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { AVATAR_COLORS } from './myBookings.constants';
import { avatarInitial, formatPickupDropoffLine } from './myBookings.utils';
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
  const { t } = useTranslation(['bookings']);
  const pickupDropoffLine = formatPickupDropoffLine(
    passenger.pickupName,
    passenger.dropoffName,
    t
  );

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
        <div className={styles.passengerNameRow}>
          <span className={styles.passengerName}>{passenger.passengerName}</span>
          <span className={styles.seatsBadge}>
            {t('bookings:seatsBooked', { count: passenger.numSeats })}
          </span>
        </div>
        {pickupDropoffLine ? (
          <div className={styles.passengerDropoff}>{pickupDropoffLine}</div>
        ) : null}
      </div>
      <div className={styles.passengerActions}>
        {passenger.status === 'pending_approval' && (
          <div className={styles.passengerPendingActions}>
            <button
              type="button"
              className={`${styles.btnOutline} ${styles.btnAccentGreen}`}
              aria-label={t('bookings:approve')}
              onClick={() => onApprove(passenger.bookingId)}
              disabled={actionBookingId === passenger.bookingId}
            >
              <Check size={15} aria-hidden />
            </button>
            <button
              type="button"
              className={`${styles.btnOutline} ${styles.btnDangerOutline}`}
              aria-label={t('bookings:reject')}
              onClick={() => onReject(passenger.bookingId)}
              disabled={actionBookingId === passenger.bookingId}
            >
              <X size={15} aria-hidden />
            </button>
            <button
              type="button"
              className={styles.btnOutline}
              aria-label={t('bookings:chat')}
              onClick={() => onOpenChat(passenger.bookingId)}
              disabled={chatLoading === passenger.bookingId}
            >
              <MessageCircle size={15} aria-hidden />
            </button>
          </div>
        )}
        {passenger.status === 'confirmed' && (
          <>
            <span className={styles.statusConfirmed}>{t('bookings:bookingStatus_approved')}</span>
            <button
              type="button"
              className={styles.btnOutline}
              aria-label={t('bookings:chat')}
              onClick={() => onOpenChat(passenger.bookingId)}
              disabled={chatLoading === passenger.bookingId}
            >
              <MessageCircle size={15} aria-hidden />
            </button>
          </>
        )}
        {passenger.status === 'rejected' && (
          <span className={styles.statusRejected}>{t('bookings:bookingStatus_rejected')}</span>
        )}
      </div>
    </li>
  );
}
