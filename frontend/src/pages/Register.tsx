import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { RegisterData } from '../context/AuthContext';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage } from '../utils/apiError';
import styles from './Register.module.css';

export default function Register() {
  const [form, setForm] = useState<RegisterData>({
    full_name: '',
    email: '',
    phone_number: '',
    password: '',
    confirm_password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !form.full_name.trim() ||
      !form.email.trim() ||
      !form.phone_number.trim() ||
      !form.password ||
      !form.confirm_password
    ) {
      setError('נא למלא את כל השדות');
      return;
    }
    if (form.password !== form.confirm_password) {
      setError('הסיסמאות אינן תואמות');
      return;
    }
    if (form.password.length < 8) {
      setError('הסיסמה: לפחות 8 תווים, אות גדולה, אות קטנה, מספר ותו מיוחד (@$!%*?&)');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await register({
        ...form,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone_number: form.phone_number.trim(),
      });
      navigate('/verify-email', { replace: true, state: { email: form.email.trim() } });
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'הרשמה נכשלה'));
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

        <h1 className={styles.title}>יצירת חשבון</h1>
        <p className={styles.subtitle}>הצטרף ל-Linkup והתחל לנסוע</p>

        <form onSubmit={handleSubmit} className={styles.form}>
          {error ? <ErrorBanner message={error} className={styles.error} /> : null}

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-name">
              שם מלא
            </label>
            <input
              id="reg-name"
              type="text"
              placeholder="שם מלא"
              value={form.full_name}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              className={styles.input}
              autoComplete="name"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-email">
              אימייל
            </label>
            <input
              id="reg-email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              className={styles.input}
              autoComplete="email"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-phone">
              טלפון
            </label>
            <input
              id="reg-phone"
              type="tel"
              placeholder="למשל 0501234567 או +972501234567"
              value={form.phone_number}
              onChange={(e) => setForm((f) => ({ ...f, phone_number: e.target.value }))}
              className={styles.input}
              autoComplete="tel"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-password">
              סיסמה
            </label>
            <input
              id="reg-password"
              type="password"
              placeholder="לפחות 8 תווים"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              className={styles.input}
              autoComplete="new-password"
            />
            <span className={styles.fieldHint}>
              חייב לכלול אות גדולה, קטנה, מספר ותו מיוחד (@$!%*?&)
            </span>
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel} htmlFor="reg-confirm">
              אימות סיסמה
            </label>
            <input
              id="reg-confirm"
              type="password"
              placeholder="הזן שוב את הסיסמה"
              value={form.confirm_password}
              onChange={(e) => setForm((f) => ({ ...f, confirm_password: e.target.value }))}
              className={styles.input}
              autoComplete="new-password"
            />
          </div>

          <LoadingButton
            type="submit"
            className={styles.button}
            loading={loading}
            loadingLabel="נרשם..."
          >
            צור חשבון
          </LoadingButton>
        </form>

        <p className={styles.link}>
          <Link to="/login">
            כבר יש חשבון? <strong>התחבר</strong>
          </Link>
        </p>
      </div>
    </div>
  );
}
