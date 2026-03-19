import { useCallback, useEffect, useMemo, useState } from 'react';
import styles from './FCMCheck.module.css';
import { initFCM } from '../services/fcm';
import { getMessagingSafe } from '../config/firebase';
import { getToken, onMessage } from 'firebase/messaging';
import { api } from '../api/client';
import { FIREBASE_VAPID_KEY, firebaseConfig } from '../config/firebase';

type PillTone = 'ok' | 'warn' | 'bad';

function pillClass(tone: PillTone) {
  if (tone === 'ok') return `${styles.pill} ${styles.pillOk}`;
  if (tone === 'warn') return `${styles.pill} ${styles.pillWarn}`;
  return `${styles.pill} ${styles.pillBad}`;
}

function formatBool(b: boolean): { text: string; tone: PillTone } {
  return b ? { text: 'כן', tone: 'ok' } : { text: 'לא', tone: 'bad' };
}

function shortToken(t?: string | null) {
  if (!t) return '';
  if (t.length <= 26) return t;
  return `${t.slice(0, 14)}…${t.slice(-10)}`;
}

export default function FCMCheck() {
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>(
    'default'
  );
  const [swSupported, setSwSupported] = useState(false);
  const [notifSupported, setNotifSupported] = useState(false);
  const [swReady, setSwReady] = useState(false);
  const [lastToken, setLastToken] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<string>('');
  const [lastError, setLastError] = useState<string>('');
  const [busy, setBusy] = useState(false);

  const envOk = useMemo(() => {
    const required = [
      firebaseConfig.apiKey,
      firebaseConfig.authDomain,
      firebaseConfig.projectId,
      firebaseConfig.storageBucket,
      firebaseConfig.messagingSenderId,
      firebaseConfig.appId,
      FIREBASE_VAPID_KEY,
    ];
    return required.every((v) => typeof v === 'string' && v.trim().length > 0);
  }, []);

  const refreshBasics = useCallback(async () => {
    const notifOk = typeof window !== 'undefined' && 'Notification' in window;
    const swOk = typeof navigator !== 'undefined' && 'serviceWorker' in navigator;
    setNotifSupported(notifOk);
    setSwSupported(swOk);
    setPermission(notifOk ? Notification.permission : 'unsupported');

    if (!swOk) {
      setSwReady(false);
      return;
    }
    try {
      const reg = await navigator.serviceWorker.getRegistration('/firebase-messaging-sw.js');
      setSwReady(Boolean(reg));
    } catch {
      setSwReady(false);
    }
  }, []);

  useEffect(() => {
    void refreshBasics();
  }, [refreshBasics]);

  useEffect(() => {
    const messaging = getMessagingSafe();
    if (!messaging) return;
    const unsub = onMessage(messaging, (payload) => {
      setLastMessage(JSON.stringify(payload, null, 2));
    });
    return () => unsub();
  }, []);

  const requestPermission = useCallback(async () => {
    setLastError('');
    if (!('Notification' in window)) {
      setPermission('unsupported');
      return;
    }
    const p = await Notification.requestPermission();
    setPermission(p);
  }, []);

  const registerSwAndSendConfig = useCallback(async () => {
    setLastError('');
    if (!('serviceWorker' in navigator)) return;
    const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
    reg.active?.postMessage({ type: 'FIREBASE_CONFIG', config: firebaseConfig });
    setSwReady(true);
  }, []);

  const getTokenOnly = useCallback(async () => {
    setLastError('');
    setBusy(true);
    try {
      const messaging = getMessagingSafe();
      if (!messaging) throw new Error('messaging unavailable (SSR?)');
      if (!('serviceWorker' in navigator)) throw new Error('serviceWorker unsupported');

      const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      registration.active?.postMessage({ type: 'FIREBASE_CONFIG', config: firebaseConfig });

      const token = await getToken(messaging, {
        vapidKey: FIREBASE_VAPID_KEY,
        serviceWorkerRegistration: registration,
      });
      setLastToken(token || null);
    } catch (e) {
      setLastError(String(e));
    } finally {
      setBusy(false);
      void refreshBasics();
    }
  }, [refreshBasics]);

  const sendTokenToServer = useCallback(async () => {
    setLastError('');
    setBusy(true);
    try {
      if (!lastToken) throw new Error('No token yet. Click "צור Token" קודם.');
      await api.patch('/users/fcm-token', { fcm_token: lastToken });
    } catch (e) {
      setLastError(String(e));
    } finally {
      setBusy(false);
    }
  }, [lastToken]);

  const runFullInit = useCallback(async () => {
    setLastError('');
    setBusy(true);
    try {
      await initFCM();
    } catch (e) {
      setLastError(String(e));
    } finally {
      setBusy(false);
      void refreshBasics();
    }
  }, [refreshBasics]);

  const clearLocal = useCallback(async () => {
    setLastError('');
    setLastMessage('');
    setLastToken(null);
    if (!('serviceWorker' in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.getRegistration('/firebase-messaging-sw.js');
      await reg?.unregister();
      setSwReady(false);
    } catch (e) {
      setLastError(String(e));
    }
  }, []);

  const permissionPill = useMemo(() => {
    if (permission === 'unsupported') return { text: 'לא נתמך', tone: 'bad' as const };
    if (permission === 'granted') return { text: 'granted', tone: 'ok' as const };
    if (permission === 'denied') return { text: 'denied', tone: 'bad' as const };
    return { text: 'default', tone: 'warn' as const };
  }, [permission]);

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>בדיקת FCM (Web Push)</h1>
          <p className={styles.subtitle}>
            מסך בדיקה ל-dev: הרשאות Notifications, Service Worker, יצירת FCM token ושליחה לשרת.
            כדי לקבל פוש ברקע צריך גם שהדפדפן יתמוך ב-Push ושיש לך VAPID + Firebase config ב-`.env`.
          </p>
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles.grid}>
          <div className={styles.item}>
            <div className={styles.itemLeft}>
              <p className={styles.label}>משתני ENV של Firebase</p>
              <p className={styles.desc}>
                נבדק שיש ערכים ל-`VITE_FIREBASE_*` וגם `VITE_FIREBASE_VAPID_KEY`.
              </p>
            </div>
            {(() => {
              const v = formatBool(envOk);
              return <span className={pillClass(v.tone)}>{v.text}</span>;
            })()}
          </div>

          <div className={styles.item}>
            <div className={styles.itemLeft}>
              <p className={styles.label}>תמיכת Notifications</p>
              <p className={styles.desc}>`window.Notification`</p>
            </div>
            {(() => {
              const v = formatBool(notifSupported);
              return <span className={pillClass(v.tone)}>{v.text}</span>;
            })()}
          </div>

          <div className={styles.item}>
            <div className={styles.itemLeft}>
              <p className={styles.label}>הרשאת Notifications</p>
              <p className={styles.desc}>`Notification.permission`</p>
            </div>
            <span className={pillClass(permissionPill.tone)}>{permissionPill.text}</span>
          </div>

          <div className={styles.item}>
            <div className={styles.itemLeft}>
              <p className={styles.label}>תמיכת Service Worker</p>
              <p className={styles.desc}>`navigator.serviceWorker`</p>
            </div>
            {(() => {
              const v = formatBool(swSupported);
              return <span className={pillClass(v.tone)}>{v.text}</span>;
            })()}
          </div>

          <div className={styles.item}>
            <div className={styles.itemLeft}>
              <p className={styles.label}>SW רשום</p>
              <p className={styles.desc}>האם קיים registration ל-`/firebase-messaging-sw.js`</p>
            </div>
            {(() => {
              const v = formatBool(swReady);
              return <span className={pillClass(v.tone)}>{v.text}</span>;
            })()}
          </div>

          <div className={styles.item}>
            <div className={styles.itemLeft}>
              <p className={styles.label}>Token (מקומי)</p>
              <p className={styles.desc}>
                נשמר בזיכרון של הדף לצורך בדיקה. (לא נשמר ב-storage)
              </p>
            </div>
            <span className={pillClass(lastToken ? 'ok' : 'warn')}>
              {lastToken ? shortToken(lastToken) : 'אין'}
            </span>
          </div>
        </div>

        <div className={styles.actions}>
          <button type="button" className={styles.btn} onClick={refreshBasics} disabled={busy}>
            רענן סטטוס
          </button>
          <button
            type="button"
            className={styles.btn}
            onClick={requestPermission}
            disabled={busy || !notifSupported}
          >
            בקש הרשאה
          </button>
          <button
            type="button"
            className={styles.btn}
            onClick={registerSwAndSendConfig}
            disabled={busy || !swSupported}
          >
            רשום SW
          </button>
          <button
            type="button"
            className={`${styles.btn} ${styles.btnPrimary}`}
            onClick={getTokenOnly}
            disabled={busy || !envOk}
          >
            צור Token
          </button>
          <button
            type="button"
            className={styles.btn}
            onClick={sendTokenToServer}
            disabled={busy || !lastToken}
          >
            שלח לשרת (PATCH)
          </button>
          <button
            type="button"
            className={styles.btn}
            onClick={runFullInit}
            disabled={busy || !envOk}
          >
            הרץ initFCM (Full)
          </button>
          <button type="button" className={`${styles.btn} ${styles.btnDanger}`} onClick={clearLocal} disabled={busy}>
            נקה / בטל רישום SW
          </button>
        </div>

        {(lastError || lastMessage) && (
          <div className={styles.monoBox}>
            {lastError && (
              <>
                <p className={styles.monoTitle}>שגיאה אחרונה</p>
                <pre className={styles.mono}>{lastError}</pre>
              </>
            )}
            {lastMessage && (
              <>
                <p className={styles.monoTitle}>Foreground message אחרון (onMessage)</p>
                <pre className={styles.mono}>{lastMessage}</pre>
              </>
            )}
          </div>
        )}

        <div className={styles.hint}>
          טיפ: כדי לבדוק Web Push “באמת” תצטרך לפתוח את האפליקציה ב-HTTPS (או localhost)
          ולוודא ש-Firebase Console מוגדר עם ה-domain הנכון.
        </div>
      </div>
    </div>
  );
}

