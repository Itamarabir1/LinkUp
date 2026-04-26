import { Link } from 'react-router-dom';
import styles from './Sablat.module.css';

/**
 */
export default function Sablat() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>סבלט</h1>
      <p className={styles.lead}>
        כאן יופיע תוכן אתר הסבלט. בינתיים זה דף מקום — אפשר לחבר כאן מסכים, קטלוג או קישורים חיצוניים.
      </p>
      <p className={styles.actions}>
        <Link to="/my-rides" className={styles.link}>
          חזרה לנסיעות
        </Link>
        {' · '}
        <Link to="/choose-destination" className={styles.link}>
          בחירת יעד
        </Link>
      </p>
    </div>
  );
}
