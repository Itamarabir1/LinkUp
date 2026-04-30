import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import type { RegisterData } from '../context/AuthContext';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import PhoneInput from '../components/PhoneInput/PhoneInput';
import { getRegisterErrorMessage } from '../utils/apiError';
import styles from './Register.module.css';

const registerSchema = z
  .object({
    full_name: z.string().min(1),
    email: z.string().email(),
    phone_number: z.string().min(1),
    password: z.string().min(8),
    confirm_password: z.string().min(1),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'error_passwords_mismatch',
    path: ['confirm_password'],
  });

type RegisterForm = z.infer<typeof registerSchema>;

export default function Register() {
  const { t } = useTranslation('auth');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      email: '',
      phone_number: '',
      password: '',
      confirm_password: '',
    },
  });

  const onSubmit = async (form: RegisterForm) => {
    setError('');
    try {
      await registerUser({
        ...form,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone_number: form.phone_number.trim(),
      } as RegisterData);
      navigate('/verify-email', { replace: true, state: { email: form.email.trim() } });
    } catch (err: unknown) {
      setError(getRegisterErrorMessage(err, t));
    }
  };

  const renderFieldError = (key: keyof RegisterForm) => {
    const fieldError = errors[key];
    if (!fieldError) return null;
    if (key === 'password' && fieldError.type === 'too_small') {
      return <span className={styles.fieldHint}>{t('error_password_too_short')}</span>;
    }
    const message = typeof fieldError.message === 'string' ? fieldError.message : '';
    return <span className={styles.fieldHint}>{t(message || 'error_fill_all')}</span>;
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

        <h1 className={styles.title}>{t('registerTitle')}</h1>
        <p className={styles.subtitle}>{t('registerSubtitle')}</p>

        <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
          {error ? <ErrorBanner message={error} className={styles.error} /> : null}

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-name">
              {t('fullName')}
            </label>
            <input
              id="reg-name"
              type="text"
              placeholder={t('fullNamePlaceholder')}
              {...register('full_name')}
              className={styles.input}
              autoComplete="name"
            />
            {renderFieldError('full_name')}
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-email">
              {t('email')}
            </label>
            <input
              id="reg-email"
              type="email"
              placeholder="you@example.com"
              {...register('email')}
              className={styles.input}
              autoComplete="email"
            />
            {renderFieldError('email')}
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-phone">
              {t('phone')}
            </label>
            <Controller
              control={control}
              name="phone_number"
              render={({ field }) => (
                <PhoneInput
                  id="reg-phone"
                  value={field.value}
                  onChange={field.onChange}
                  defaultCountryCode="IL"
                  error={Boolean(errors.phone_number)}
                />
              )}
            />
            {renderFieldError('phone_number')}
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-password">
              {t('password')}
            </label>
            <div className={styles.passwordWrapper}>
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                placeholder={t('passwordPlaceholder')}
                {...register('password')}
                className={`${styles.input} ${styles.passwordInput}`}
                autoComplete="new-password"
              />
              <button
                type="button"
                className={styles.eyeBtn}
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? t('hidePassword') : t('showPassword')}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            <span className={styles.fieldHint}>{t('passwordHint')}</span>
            {renderFieldError('password')}
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-confirm">
              {t('confirmPassword')}
            </label>
            <input
              id="reg-confirm"
              type="password"
              placeholder={t('confirmPasswordPlaceholder')}
              {...register('confirm_password')}
              className={styles.input}
              autoComplete="new-password"
            />
            {renderFieldError('confirm_password')}
          </div>

          <LoadingButton
            type="submit"
            className={styles.button}
            loading={isSubmitting}
            loadingLabel={t('registering')}
          >
            {t('register')}
          </LoadingButton>
        </form>

        <p className={styles.link}>
          <Link to="/login">
            {t('alreadyHaveAccount')} <strong>{t('signIn')}</strong>
          </Link>
        </p>
      </div>
    </div>
  );
}
