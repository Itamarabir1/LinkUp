import type { ReactNode } from 'react';
import styles from './ErrorBanner.module.css';

export interface ErrorBannerProps {
  message: string;
  /** Optional trailing content after message (e.g. a link). */
  children?: ReactNode;
  /** default = full banner; compact = narrow row (copy/map/card). */
  variant?: 'default' | 'compact';
  /** ARIA role for accessibility semantics. */
  role?: 'alert' | 'status';
  className?: string;
}

/** Shared, reusable error banner for pages/components. */
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
