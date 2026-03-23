import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleSignIn from '../components/GoogleSignIn/GoogleSignIn.tsx';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { ERROR_MESSAGES } from '../config/constants';
import { getApiErrorMessage, isTimeoutOrAbortError } from '../utils/apiError';
import styles from './Login.module.css';

export default function Login() {
  const location = useLocation();
  const state = location.state as { email?: string; verified?: boolean; from?: { pathname: string; search?: string } } | null;
  const [email, setEmail] = useState(state?.email ?? '');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [verifiedMessage] = useState(Boolean(state?.verified));
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('נא למלא אימייל וסיסמה');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(email.trim(), password);
      const searchParams = new URLSearchParams(location.search);
      const fromQuery = searchParams.get('from');
      if (fromQuery) {
        navigate(decodeURIComponent(fromQuery), { replace: true });
        return;
      }
      const fromState = state?.from;
      const path = fromState ? `${fromState.pathname}${fromState.search ?? ''}` : '/';
      navigate(path, { replace: true });
    } catch (err: unknown) {
      if (isTimeoutOrAbortError(err)) {
        setError(ERROR_MESSAGES.BACKEND_TIMEOUT);
        return;
      }
      setError(getApiErrorMessage(err, 'התחברות נכשלה'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>התחברות</h1>
      {verifiedMessage && (
        <p className={styles.verifiedBanner}>החשבון אומת. התחבר כעת.</p>
      )}
      <form onSubmit={handleLogin} className={styles.form}>
        {error ? <ErrorBanner message={error} className={styles.error} /> : null}
        <input
          type="email"
          placeholder="אימייל"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={styles.input}
          autoComplete="email"
        />
        <input
          type="password"
          placeholder="סיסמה"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={styles.input}
          autoComplete="current-password"
        />
        <LoadingButton
          type="submit"
          className={styles.button}
          loading={loading}
          loadingLabel="מתחבר..."
        >
          התחבר
        </LoadingButton>
      </form>
      
      <div className={styles.divider}>
        <div className={styles.dividerLine} aria-hidden />
        <span className={styles.dividerLabel}>או</span>
      </div>

      <GoogleSignIn onError={setError} disabled={loading} />

      <p className={styles.link}>
        <Link to="/register">אין חשבון? הירשם</Link>
      </p>
    </div>
  );
}
