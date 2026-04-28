import { useState } from 'react';
import { Mail } from 'lucide-react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { resendVerificationEmail, verifyEmailCode } from '../api/auth';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage } from '../utils/apiError';
import styles from './VerifyEmail.module.css';

const verifySchema = z.object({
  code: z.string().length(6).regex(/^\d+$/),
});

type VerifyForm = z.infer<typeof verifySchema>;

export default function VerifyEmail() {
  const { t } = useTranslation('auth');
  const location = useLocation();
  const navigate = useNavigate();
  const emailFromState = (location.state as { email?: string } | null)?.email;
  const emailFromQuery = new URLSearchParams(location.search).get('email');
  const email = emailFromState ?? emailFromQuery ?? '';

  const [resendLoading, setResendLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<VerifyForm>({
    resolver: zodResolver(verifySchema),
    defaultValues: { code: '' },
  });

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
          <h1 className={styles.title}>{t('verifyAccountTitle')}</h1>
          <p className={styles.intro}>{t('error_missing_email_for_verify')}</p>
          <p className={styles.link}>
            <Link to="/register">{t('registration')}</Link>
            {' · '}
            <Link to="/login">{t('loginLink')}</Link>
          </p>
        </div>
      </div>
    );
  }

  const handleVerify = async ({ code }: VerifyForm) => {
    setError('');
    setSuccess('');
    try {
      await verifyEmailCode(email, code.trim());
      setSuccess(t('verify_success'));
      setTimeout(() => {
        navigate('/login', { replace: true, state: { email, verified: true } });
      }, 1200);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t('error_verify_failed')));
    }
  };

  const handleResend = async () => {
    setError('');
    setSuccess('');
    setResendLoading(true);
    try {
      await resendVerificationEmail(email);
      setSuccess(t('resend_success'));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, t('error_resend_failed')));
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

        <h1 className={styles.title}>{t('checkInboxTitle')}</h1>
        <p className={styles.intro}>
          {t('verificationIntroPrefix')}<strong>{email}</strong>.<br />
          {t('verificationIntro2')}
        </p>

        <form onSubmit={handleSubmit(handleVerify)}>
          {error ? <ErrorBanner message={error} className={styles.error} /> : null}
          {success ? <p className={styles.successText}>{success}</p> : null}

          <div className={styles.otpWrap}>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              className={styles.otpDigit}
              maxLength={6}
              {...register('code')}
              onChange={(e) => {
                setValue('code', e.target.value.replace(/\D/g, '').slice(0, 6), {
                  shouldValidate: true,
                });
              }}
              placeholder={t('verificationCodePlaceholder')}
              aria-label={t('verificationCode')}
            />
          </div>
          {errors.code ? <p className={styles.error}>{t('error_missing_verification_code')}</p> : null}

          <LoadingButton
            type="submit"
            className={styles.button}
            loading={isSubmitting}
            loadingLabel={t('verifying')}
          >
            {t('verifyAccountButton')}
          </LoadingButton>
        </form>

        <p className={`${styles.link} ${styles.linkSpaced}`}>
          <LoadingButton
            type="button"
            className={styles.resendBtn}
            loading={resendLoading}
            loadingLabel={t('sending')}
            onClick={handleResend}
          >
            {t('resendNewCode')}
          </LoadingButton>
        </p>
        <p className={styles.link}>
          <Link to="/login">{t('backToLogin')}</Link>
        </p>
      </div>
    </div>
  );
}
