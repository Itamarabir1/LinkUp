import type { ReactNode } from 'react';
import styles from './MyBookings.module.css';

export interface BookingCardActionBarProps {
  children: ReactNode;
}

export function BookingCardActionBar({ children }: BookingCardActionBarProps) {
  return <div className={styles.cardActionBar}>{children}</div>;
}
