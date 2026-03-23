import type { ButtonHTMLAttributes, ReactNode } from 'react';
import styles from './LoadingButton.module.css';

export interface LoadingButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  children: ReactNode;
  loading: boolean;
  loadingLabel?: string;
}

/** כפתור עם מצב טעינה אחיד */
export default function LoadingButton({
  children,
  loading,
  loadingLabel = 'טוען...',
  disabled,
  className = '',
  type = 'button',
  ...rest
}: LoadingButtonProps) {
  const cls = className?.trim() ? className : styles.btn;

  return (
    <button
      type={type}
      className={cls}
      disabled={disabled || loading}
      aria-busy={loading}
      {...rest}
    >
      {loading ? loadingLabel : children}
    </button>
  );
}
