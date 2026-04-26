import { XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { useCreateCheckoutSession } from '../../features/billing/mutations';
import styles from './PaymentCancel.module.css';

export default function PaymentCancel() {
  const { t } = useTranslation('billing');
  const checkout = useCreateCheckoutSession();

  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <XCircle size={64} className={styles.icon} aria-hidden="true" />
        <h1 className={styles.title}>{t('paymentCancelTitle')}</h1>
        <p className={styles.subtitle}>{t('paymentCancelSubtitle')}</p>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.primaryBtn}
            onClick={() => checkout.mutate()}
            disabled={checkout.isPending}
          >
            {checkout.isPending ? t('upgradeLoading') : t('tryAgain')}
          </button>
          <Link className={styles.ghostBtn} to="/profile">
            {t('backToProfile')}
          </Link>
        </div>
      </section>
    </div>
  );
}
