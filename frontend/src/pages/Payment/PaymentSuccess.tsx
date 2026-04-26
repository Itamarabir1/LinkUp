import { useMemo, useRef } from 'react';
import { CheckCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useBillingStatus } from '../../features/billing/queries';
import styles from './PaymentSuccess.module.css';

const POLL_INTERVAL_MS = 2000;
const TIMEOUT_MS = 30_000;

export default function PaymentSuccess() {
  const { t } = useTranslation('billing');
  const startedAtRef = useRef<number>(Date.now());
  const { data } = useBillingStatus({
    refetchInterval: (query) => {
      const timedOut = Date.now() - startedAtRef.current >= TIMEOUT_MS;
      if (timedOut || query.state.error || query.state.data?.is_premium) return false;
      return POLL_INTERVAL_MS;
    },
  });
  const isTimedOut = Date.now() - startedAtRef.current >= TIMEOUT_MS;

  const statusText = useMemo(() => {
    if (data?.is_premium) return t('paymentSuccessVerified');
    if (isTimedOut) return t('paymentSuccessTimeout');
    return t('paymentSuccessPolling');
  }, [data?.is_premium, isTimedOut, t]);

  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <CheckCircle size={64} className={styles.icon} aria-hidden="true" />
        <h1 className={styles.title}>{t('paymentSuccessTitle')}</h1>
        <p className={styles.subtitle}>{t('paymentSuccessSubtitle')}</p>
        <p className={styles.status}>{statusText}</p>
        <Link className={styles.primaryBtn} to="/profile">
          {t('backToProfile')}
        </Link>
      </section>
    </div>
  );
}
