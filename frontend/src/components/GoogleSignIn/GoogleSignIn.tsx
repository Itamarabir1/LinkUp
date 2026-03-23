import { useGoogleSignIn } from './useGoogleSignIn';
import styles from './GoogleSignIn.module.css';

export interface GoogleSignInProps {
  onError?: (error: string) => void;
  disabled?: boolean;
}

export default function GoogleSignIn({ onError, disabled }: GoogleSignInProps) {
  const { buttonRef, scriptLoaded, loading } = useGoogleSignIn({ onError, disabled });

  if (!scriptLoaded) {
    return (
      <div ref={buttonRef} className={styles.placeholder}>
        {loading ? 'מתחבר...' : 'טוען Google Sign-In...'}
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
