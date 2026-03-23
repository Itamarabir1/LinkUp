import styles from './FCMCheck.module.css';
import type { PermissionPillTone } from './useFCMCheck';
import { useFCMCheck } from './useFCMCheck';

function pillClass(tone: PermissionPillTone) {
  if (tone === 'ok') return `${styles.pill} ${styles.pillOk}`;
  if (tone === 'warn') return `${styles.pill} ${styles.pillWarn}`;
  return `${styles.pill} ${styles.pillBad}`;
}

function formatBool(b: boolean): { text: string; tone: PermissionPillTone } {
  return b ? { text: 'כן', tone: 'ok' } : { text: 'לא', tone: 'bad' };
}

function shortToken(t?: string | null) {
  if (!t) return '';
  if (t.length <= 26) return t;
  return `${t.slice(0, 14)}…${t.slice(-10)}`;
}

export default function FCMCheck() {
  const {
    envOk,
    notifSupported,
    swSupported,
    swReady,
    lastToken,
    lastMessage,
    lastError,
    busy,
    permissionPill,
    refreshBasics,
    requestPermission,
    registerSwAndSendConfig,
    getTokenOnly,
    sendTokenToServer,
    runFullInit,
    clearLocal,
  } = useFCMCheck();

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
