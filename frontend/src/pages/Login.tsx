import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import GoogleSignIn from '../components/GoogleSignIn/GoogleSignIn.tsx';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { ERROR_MESSAGES } from '../config/constants';
import { getApiErrorMessage, isTimeoutOrAbortError } from '../utils/apiError';
import styles from './Login.module.css';

export default function Login() {
  const { t } = useTranslation('auth');
  const location = useLocation();
  const state = location.state as {
    email?: string;
    verified?: boolean;
    from?: { pathname: string; search?: string };
  } | null;
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
      setError(t('error_email_password'));
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
      if (fromState) {
        navigate(`${fromState.pathname}${fromState.search ?? ''}`, { replace: true });
        return;
      }
      navigate('/choose-destination', { replace: true });
    } catch (err: unknown) {
      if (isTimeoutOrAbortError(err)) {
        setError(ERROR_MESSAGES.BACKEND_TIMEOUT);
        return;
      }
      setError(getApiErrorMessage(err, t('error_login_failed')));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logoWrap}>
          <div className={styles.logoIcon}>
            <svg
              width="26"
              height="26"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 17H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h11l4 4h1a2 2 0 0 1 2 2v2h-2" />
              <circle cx="7" cy="17" r="2" />
              <circle cx="17" cy="17" r="2" />
            </svg>
          </div>
        </div>

        <h1 className={styles.title}>{t('welcomeBack')}</h1>
        <p className={styles.subtitle}>{t('loginSubtitle')}.</p>

        {verifiedMessage ? (
          <p className={styles.verifiedBanner}>✓ {t('emailVerified')}</p>
        ) : null}

        <form onSubmit={handleLogin} className={styles.form}>
          {error ? <ErrorBanner message={error} className={styles.error} /> : null}

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="login-email">
              {t('email')}
            </label>
            <input
              id="login-email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={styles.input}
              autoComplete="email"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="login-password">
              {t('password')}
            </label>
            <input
              id="login-password"
              type="password"
              placeholder={t('passwordPlaceholder')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={styles.input}
              autoComplete="current-password"
            />
          </div>

          <LoadingButton
            type="submit"
            className={styles.button}
            loading={loading}
            loadingLabel={t('loggingIn')}
          >
            {t('login')}
          </LoadingButton>
        </form>

        <div className={styles.divider}>
          <div className={styles.dividerLine} aria-hidden />
          <span className={styles.dividerLabel}>{t('orContinueWith')}</span>
        </div>

        <GoogleSignIn onError={setError} disabled={loading} />

        <p className={styles.link}>
          <Link to="/register">
            {t('noAccount')} <strong>{t('signUp')}</strong>
          </Link>
        </p>
      </div>
    </div>
  );
}
