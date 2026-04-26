import { useGoogleSignIn } from './useGoogleSignIn';
import { useTranslation } from 'react-i18next';
import styles from './GoogleSignIn.module.css';

export interface GoogleSignInProps {
  onError?: (error: string) => void;
  disabled?: boolean;
}

export default function GoogleSignIn({ onError, disabled }: GoogleSignInProps) {
  const { t } = useTranslation('auth');
  const { buttonRef, scriptLoaded, loading } = useGoogleSignIn({ onError, disabled });

  if (!scriptLoaded) {
    return (
      <div ref={buttonRef} className={styles.placeholder}>
        {loading ? t('loggingIn') : t('continueWithGoogle')}
      </div>
    );
  }

  return (
    <div
      ref={buttonRef}
      className={`${styles.container} ${disabled ? styles.containerDisabled : ''}`}
    />
  );
}
