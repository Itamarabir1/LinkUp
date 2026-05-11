import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useAuth } from '../context/AuthContext';
import GoogleSignIn from '../components/GoogleSignIn/GoogleSignIn.tsx';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage, isTimeoutOrAbortError } from '../utils/apiError';
import styles from './Login.module.css';

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function Login() {
  const { t } = useTranslation('auth');
  const location = useLocation();
  const state = location.state as {
    email?: string;
    verified?: boolean;
    from?: { pathname: string; search?: string };
  } | null;
  const [error, setError] = useState('');
  const [verifiedMessage] = useState(Boolean(state?.verified));
  const { register, handleSubmit, clearErrors, formState } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: state?.email ?? '',
      password: '',
    },
  });
  const { login } = useAuth();
  const navigate = useNavigate();

  const onSubmit = async ({ email, password }: LoginForm) => {
    setError('');
    clearErrors();
    try {
      await login(email.trim(), password);
      const searchParams = new URLSearchParams(location.search);
      const fromQuery = searchParams.get('from');
      if (fromQuery) {
        const decoded = decodeURIComponent(fromQuery);
        if (decoded.startsWith('/') && !decoded.startsWith('//')) {
          navigate(decoded, { replace: true });
          return;
        }
      }
      const fromState = state?.from;
      if (fromState) {
        navigate(`${fromState.pathname}${fromState.search ?? ''}`, { replace: true });
        return;
      }
      navigate('/choose-destination', { replace: true });
    } catch (err: unknown) {
      if (isTimeoutOrAbortError(err)) {
        setError(t('backend_timeout'));
        return;
      }
      setError(getApiErrorMessage(err, t('error_login_failed')));
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
        <p className={styles.subtitle}>{t('loginSubtitle')}</p>

        {verifiedMessage ? (
          <p className={styles.verifiedBanner}>✓ {t('emailVerified')}</p>
        ) : null}

        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          {error ? <ErrorBanner message={error} className={styles.error} /> : null}

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="login-email">
              {t('email')}
            </label>
            <input
              id="login-email"
              type="email"
              placeholder="you@example.com"
              {...register('email')}
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
              {...register('password')}
              className={styles.input}
              autoComplete="current-password"
            />
          </div>

          <LoadingButton
            type="submit"
            className={styles.button}
            loading={formState.isSubmitting}
            loadingLabel={t('loggingIn')}
          >
            {t('login')}
          </LoadingButton>
        </form>

        <div className={styles.divider}>
          <div className={styles.dividerLine} aria-hidden />
          <span className={styles.dividerLabel}>{t('orContinueWith')}</span>
        </div>

        <GoogleSignIn onError={setError} disabled={formState.isSubmitting} />

        <p className={styles.link}>
          <Link to="/register">
            {t('noAccount')} <strong>{t('signUp')}</strong>
          </Link>
        </p>
      </div>
    </div>
  );
}
