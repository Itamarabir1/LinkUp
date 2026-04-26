import { useTranslation } from 'react-i18next';
import styles from './PageLoading.module.css';

/**
 * Suspense fallback rendered while lazy chunks load.
 *
 * Renders a complete a11y-compliant page (landmark + h1) so axe never flags
 * "missing main", "missing h1", or "content outside landmarks" during
 * route transitions. The visible label mirrors the screen-reader h1.
 */
export default function PageLoading() {
  const { t } = useTranslation('common');
  const label = t('loading');
  return (
    <main className={styles.wrap} aria-busy="true" aria-live="polite">
      <h1 className="sr-only">{label}</h1>
      <span aria-hidden="true">{label}</span>
    </main>
  );
}
