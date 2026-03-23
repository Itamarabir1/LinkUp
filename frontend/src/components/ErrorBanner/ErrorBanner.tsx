import type { ReactNode } from 'react';
import styles from './ErrorBanner.module.css';

export interface ErrorBannerProps {
  message: string;
  /** תוכן נוסף אחרי ההודעה (למשל קישור) */
  children?: ReactNode;
  /** default = קופסה מלאה; compact = שורה צרה (העתקה, מפה, כרטיס) */
  variant?: 'default' | 'compact';
  /** תפקיד ל-a11y */
  role?: 'alert' | 'status';
  className?: string;
}

/** הודעת שגיאה אחידה לדפים */
export default function ErrorBanner({
  message,
  children,
  variant = 'default',
  role = 'alert',
  className = '',
}: ErrorBannerProps) {
  if (!message.trim() && !children) return null;
  const variantClass = variant === 'compact' ? styles.compact : '';
  return (
    <p className={`${styles.banner} ${variantClass} ${className}`.trim()} role={role}>
      {message}
      {children}
    </p>
  );
}
