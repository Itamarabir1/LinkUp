import styles from './RideCard.module.css';

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  success: { bg: 'var(--success-bg)', text: 'var(--success-text)' },
  warning: { bg: 'var(--warning-bg)', text: 'var(--warning-text)' },
  danger: { bg: 'var(--danger-bg)', text: 'var(--danger-text)' },
  info: { bg: 'var(--info-bg)', text: 'var(--info-text)' },
  neutral: { bg: 'var(--neutral-bg)', text: 'var(--neutral-text)' },
};

function getStatusVariant(status: string): keyof typeof STATUS_STYLES {
  const s = status.toLowerCase();
  if (s.includes('מלא') || s.includes('ממתין')) return 'warning';
  if (s.includes('בוטל') || s.includes('נדחה')) return 'danger';
  if (s.includes('מחפש')) return 'info';
  if (s.includes('פג תוקף')) return 'neutral';
  return 'success';
}

interface RideCardProps {
  route: string;
  /** תאריך ושעה של הנסיעה/הבקשה (לא זמן יצירה באתר) */
  time: string;
  /** כותרת מעל השעה, למשל "זמן הנסיעה" */
  scheduleCaption?: string;
  status: string;
  source?: string;
  onClick?: () => void;
}

export default function RideCard({
  route,
  time,
  scheduleCaption,
  status,
  source,
  onClick,
}: RideCardProps) {
  const variant = getStatusVariant(status);
  const style = STATUS_STYLES[variant] ?? STATUS_STYLES.neutral;

  return (
    <article
      className={styles.card}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <div className={styles.route}>{route}</div>
      {scheduleCaption ? (
        <div className={styles.scheduleBlock}>
          <span className={styles.scheduleCaption}>{scheduleCaption}</span>
          <span className={styles.time}>{time || '—'}</span>
        </div>
      ) : (
        <div className={styles.time}>{time}</div>
      )}
      <div className={styles.footer}>
        <span
          className={styles.badge}
          style={{ backgroundColor: style.bg, color: style.text }}
        >
          {status}
        </span>
        {source && <span className={styles.source}>{source}</span>}
      </div>
    </article>
  );
}
