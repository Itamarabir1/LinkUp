import { useNavigate } from 'react-router-dom';
import { Car, Store } from 'lucide-react';
import styles from './PostLoginHub.module.css';

export default function PostLoginHub() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>לאן נמשיך?</h1>
      <p className={styles.subtitle}>בחר לאיזה חלק באפליקציה תרצה לעבור</p>
      <div className={styles.cards}>
        <button
          type="button"
          className={styles.card}
          onClick={() => navigate('/my-rides')}
        >
          <span className={styles.iconWrap} aria-hidden>
            <Car size={36} strokeWidth={1.5} />
          </span>
          <span className={styles.cardTitle}>לאתר הנסיעות</span>
          <span className={styles.cardHint}>הנסיעות שלי, חיפוש, הזמנות וקבוצות</span>
        </button>
        <button
          type="button"
          className={styles.card}
          onClick={() => navigate('/sablat')}
        >
          <span className={styles.iconWrap} aria-hidden>
            <Store size={36} strokeWidth={1.5} />
          </span>
          <span className={styles.cardTitle}>לאתר סבלט</span>
          <span className={styles.cardHint}>אזור סבלט (חדש)</span>
        </button>
      </div>
    </div>
  );
}
