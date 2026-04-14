import { useState } from 'react';
import { Mail } from 'lucide-react';
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
        <div className={styles.card}>
          <div className={styles.logoWrap}>
            <div className={styles.logoIcon}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h11l4 4h1a2 2 0 0 1 2 2v2h-2" />
                <circle cx="7" cy="17" r="2" /><circle cx="17" cy="17" r="2" />
              </svg>
            </div>
          </div>
          <h1 className={styles.title}>אימות חשבון מייל</h1>
          <p className={styles.intro}>לא נמצא אימייל לאימות. נסה להירשם או להיכנס מחדש.</p>
          <p className={styles.link}>
            <Link to="/register">הרשמה</Link>
            {' · '}
            <Link to="/login">התחברות</Link>
          </p>
        </div>
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
      <div className={styles.card}>
        <div className={styles.logoWrap}>
          <div className={styles.logoIcon}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h11l4 4h1a2 2 0 0 1 2 2v2h-2" />
              <circle cx="7" cy="17" r="2" /><circle cx="17" cy="17" r="2" />
            </svg>
          </div>
        </div>

        <div className={styles.emailIconWrap}>
          <div className={styles.emailCircle}>
            <Mail size={32} strokeWidth={1.5} color="var(--primary)" />
          </div>
        </div>

        <h1 className={styles.title}>בדוק את האימייל שלך</h1>
        <p className={styles.intro}>
          שלחנו קוד אימות ל-<strong>{email}</strong>.<br />
          הזן את הקוד כדי לאמת את החשבון.
        </p>

        <form onSubmit={handleVerify}>
          {error ? <ErrorBanner message={error} className={styles.error} /> : null}
          {success ? <p className={styles.successText}>{success}</p> : null}

          <div className={styles.otpWrap}>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              className={styles.otpDigit}
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="······"
              aria-label="קוד אימות"
            />
          </div>

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
            שלח קוד חדש
          </LoadingButton>
        </p>
        <p className={styles.link}>
          <Link to="/login">חזרה להתחברות</Link>
        </p>
      </div>
    </div>
  );
}
