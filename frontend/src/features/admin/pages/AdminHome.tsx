import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchAdminStats, type AdminStatsResponse } from '../api/stats';
import page from '../styles/AdminPage.module.css';
import styles from './AdminHome.module.css';

type State =
  | { status: 'loading' }
  | { status: 'ready'; data: AdminStatsResponse }
  | { status: 'error' };

export default function AdminHome() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await fetchAdminStats();
        if (!mounted) return;
        setState({ status: 'ready', data });
      } catch {
        if (!mounted) return;
        setState({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div>
      <h2 className={page.pageTitle}>לוח בקרה</h2>
      <p className={styles.intro}>
        סקירה מהירה של מצב המערכת. לחיצה על כרטיס מובילה למסך הרלוונטי.
      </p>

      {state.status === 'loading' && <p className={page.muted}>טוען נתונים…</p>}
      {state.status === 'error' && (
        <p className={page.error}>לא ניתן לטעון סטטיסטיקות.</p>
      )}
      {state.status === 'ready' && (
        <div className={styles.statsGrid}>
          <Link to="/admin/users" className={styles.statCard}>
            <p className={styles.statLabel}>סה״כ משתמשים</p>
            <p className={styles.statValue}>{state.data.users_total}</p>
            <p className={styles.statHint}>ניהול משתמשים ←</p>
          </Link>
          <Link to="/admin/rides" className={styles.statCard}>
            <p className={styles.statLabel}>נסיעות פעילות</p>
            <p className={styles.statValue}>{state.data.rides_active}</p>
            <p className={styles.statHint}>open / full / active</p>
          </Link>
          <Link to="/admin/lookup" className={styles.statCard}>
            <p className={styles.statLabel}>סה״כ הזמנות</p>
            <p className={styles.statValue}>{state.data.bookings_total}</p>
            <p className={styles.statHint}>חיפוש לפי מזהה</p>
          </Link>
          <Link to="/admin/outbox" className={styles.statCard}>
            <p className={styles.statLabel}>Outbox ממתין</p>
            <p className={styles.statValue}>{state.data.outbox_pending}</p>
            <p className={styles.statHint}>תור אירועים ←</p>
          </Link>
        </div>
      )}

      <h3 className={styles.sectionTitle}>קישורים מהירים</h3>
      <div className={styles.quickLinks}>
        <Link to="/admin/health" className={styles.quickLink}>
          בריאות מערכת
        </Link>
        <Link to="/admin/groups" className={styles.quickLink}>
          קבוצות
        </Link>
        <Link to="/admin/lookup" className={styles.quickLink}>
          חיפוש נסיעה / הזמנה
        </Link>
      </div>
    </div>
  );
}
