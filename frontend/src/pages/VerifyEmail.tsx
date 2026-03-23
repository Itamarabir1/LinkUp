import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { resendVerificationEmail, verifyEmailCode } from '../api/auth';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage } from '../utils/apiError';
import styles from './VerifyEmail.module.css';

export default function VerifyEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const emailFromState = (location.state as { email?: string } | null)?.email;
  const emailFromQuery = new URLSearchParams(location.search).get('email');
  const email = emailFromState ?? emailFromQuery ?? '';

  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  if (!email) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>אימות חשבון מייל</h1>
        <p className={styles.error}>לא נמצא אימייל לאימות. נא להירשם או להיכנס מחדש.</p>
        <p className={styles.link}>
          <Link to="/register">הרשמה</Link> · <Link to="/login">התחברות</Link>
        </p>
      </div>
    );
  }

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) {
      setError('נא להזין את הקוד שנשלח למייל');
      return;
    }
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await verifyEmailCode(email, code.trim());
      setSuccess('החשבון אומת בהצלחה.');
      setTimeout(() => {
        navigate('/login', { replace: true, state: { email, verified: true } });
      }, 1200);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'אימות נכשל'));
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setSuccess('');
    setResendLoading(true);
    try {
      await resendVerificationEmail(email);
      setSuccess('קוד חדש נשלח למייל.');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'שליחת קוד מחדש נכשלה'));
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>אימות חשבון מייל</h1>
      <p className={styles.intro}>
        נשלח קוד אימות ל־<strong>{email}</strong>. הזן את הקוד למטה.
      </p>
      <form onSubmit={handleVerify} className={styles.form}>
        {error ? <ErrorBanner message={error} className={styles.error} /> : null}
        {success && <p className={styles.successText}>{success}</p>}
        <input
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="קוד אימות (6 ספרות)"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
          className={styles.input}
          maxLength={6}
        />
        <LoadingButton
          type="submit"
          className={styles.button}
          loading={loading}
          loadingLabel="מאמת..."
        >
          אמת חשבון
        </LoadingButton>
      </form>
      <p className={`${styles.link} ${styles.linkSpaced}`}>
        <LoadingButton
          type="button"
          className={styles.resendBtn}
          loading={resendLoading}
          loadingLabel="שולח..."
          onClick={handleResend}
        >
          שלח קוד שוב
        </LoadingButton>
      </p>
      <p className={styles.link}>
        <Link to="/login">חזרה להתחברות</Link>
      </p>
    </div>
  );
}
