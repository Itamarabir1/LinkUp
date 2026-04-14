import { useTranslation } from 'react-i18next';
import { useLang } from '../../context/LangContext';
import styles from './LangToggle.module.css';

export default function LangToggle() {
  const { toggleLang } = useLang();
  const { t } = useTranslation('common');

  return (
    <button
      type="button"
      className={styles.button}
      onClick={toggleLang}
      aria-label={t('lang_toggle_aria')}
      title={t('lang_toggle_aria')}
    >
      {t('lang_toggle_label')}
    </button>
  );
}
