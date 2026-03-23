import { useEffect, useState } from 'react';
import { setShowToastFn, type ToastData } from './notificationToast.utils';
import styles from './NotificationToast.module.css';

export function NotificationToast() {
  const [toast, setToast] = useState<ToastData | null>(null);

  useEffect(() => {
    setShowToastFn(setToast);
    return () => setShowToastFn(null);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(timer);
  }, [toast]);

  if (!toast) return null;

  return (
    <div className={styles.toast}>
      <div className={styles.icon}>🔔</div>
      <div className={styles.content}>
        <p className={styles.title}>{toast.title}</p>
        {toast.body && <p className={styles.body}>{toast.body}</p>}
      </div>
      <button className={styles.close} onClick={() => setToast(null)}>✕</button>
    </div>
  );
}
