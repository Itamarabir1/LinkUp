import { Check, Crown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatDateFull } from '../../utils/date';
import styles from './PremiumBanner.module.css';

type PremiumBannerBadgeProps = {
  mode: 'badge';
  premiumSince: string | null;
};

type PremiumBannerUpgradeProps = {
  mode: 'upgrade';
  loading?: boolean;
  onUpgrade: () => void;
};

type PremiumBannerProps = PremiumBannerBadgeProps | PremiumBannerUpgradeProps;

export default function PremiumBanner(props: PremiumBannerProps) {
  const { t } = useTranslation('billing');

  if (props.mode === 'badge') {
    return (
      <section className={`${styles.banner} ${styles.badge}`} aria-live="polite">
        <div className={styles.textBlock}>
          <p className={styles.title}>{t('premiumActive')}</p>
          <p className={styles.subtitle}>
            {props.premiumSince
              ? t('premiumSince', { date: formatDateFull(props.premiumSince) })
              : t('premiumSinceUnknown')}
          </p>
        </div>
        <span className={styles.iconWrap} aria-hidden="true">
          <Check size={20} />
        </span>
      </section>
    );
  }

  return (
    <section className={`${styles.banner} ${styles.upgrade}`} aria-live="polite">
      <button
        type="button"
        className={styles.cta}
        onClick={props.onUpgrade}
        disabled={props.loading}
      >
        {props.loading ? t('upgradeLoading') : t('upgradeNow')}
      </button>
      <div className={styles.textBlock}>
        <p className={styles.title}>{t('upgradeTitle')}</p>
        <p className={styles.subtitle}>{t('upgradeSubtitle')}</p>
      </div>
      <span className={styles.iconWrap} aria-hidden="true">
        <Crown size={20} />
      </span>
    </section>
  );
}
