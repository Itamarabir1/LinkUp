import { useTranslation } from 'react-i18next';
import styles from './PageLoading.module.css';

export default function PageLoading() {
  const { t } = useTranslation('common');
  return (
    <main className={styles.wrap} aria-busy="true" aria-live="polite">
      <h1 className="sr-only">{t('loading')}</h1>
      <div className={styles.roadWrap}>
        <div className={styles.carWrap}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" width="80" height="80">
            <g stroke="#FFFFFF" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
              <animateTransform attributeName="transform" type="translate" values="0 0;0 -1;0 0;0 1;0 0" dur="900ms" repeatCount="indefinite" />
              <path d="M18 44H14a4 4 0 0 1-4-4V28a4 4 0 0 1 4-4h26l10 10h2a4 4 0 0 1 4 4v4h-4" />
              <circle cx="24" cy="44" r="5" />
              <circle cx="44" cy="44" r="5" />
            </g>
            <circle cx="24" cy="44" r="7" stroke="#FFFFFF" strokeOpacity="0.35" strokeWidth="1.5" fill="none">
              <animateTransform attributeName="transform" type="rotate" from="0 24 44" to="360 24 44" dur="700ms" repeatCount="indefinite" />
            </circle>
            <circle cx="44" cy="44" r="7" stroke="#FFFFFF" strokeOpacity="0.35" strokeWidth="1.5" fill="none">
              <animateTransform attributeName="transform" type="rotate" from="0 44 44" to="360 44 44" dur="700ms" repeatCount="indefinite" />
            </circle>
          </svg>
        </div>
        <div className={styles.roadLine} />
        <div className={styles.dashes}>
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={i} className={styles.dash} />
          ))}
        </div>
      </div>
      <div className={styles.appName}>LinkUp</div>
      <div className={styles.dots}>
        <div className={styles.dot} />
        <div className={styles.dot} />
        <div className={styles.dot} />
      </div>
    </main>
  );
}
