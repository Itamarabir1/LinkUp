import { useEffect, useState } from 'react';
import styles from './NotificationToast.module.css';

interface ToastData {
  title: string;
  body: string;
}

let showToastFn: ((data: ToastData) => void) | null = null;

export function triggerNotificationToast(data: ToastData) {
  showToastFn?.(data);
}

export function NotificationToast() {
  const [toast, setToast] = useState<ToastData | null>(null);

  useEffect(() => {
    showToastFn = setToast;
    return () => { showToastFn = null; };
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
