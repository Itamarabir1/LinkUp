import { useEffect, useState, useRef } from 'react';
import { Camera } from 'lucide-react';
import {
  createGroup,
  getGroupImageUploadUrl,
  confirmGroupImage,
} from '../api/groups';
import { useGroup } from '../context/GroupContext';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { getApiErrorMessage } from '../utils/apiError';
import styles from './CreateGroup.module.css';

const DESCRIPTION_MAX = 500;

export default function CreateGroup() {
  const { refreshGroups } = useGroup();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [createdGroup, setCreatedGroup] = useState<{ inviteCode: string; name: string } | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setImageFile(file);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(file ? URL.createObjectURL(file) : null);
    e.target.value = '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError('');
    setImageError(null);
    try {
      const group = await createGroup({
        name: trimmed,
        description: description.trim().slice(0, DESCRIPTION_MAX) || undefined,
      });
      if (imageFile && group.group_id) {
        try {
          const { upload_url, key } = await getGroupImageUploadUrl(group.group_id);
          const putRes = await fetch(upload_url, {
            method: 'PUT',
            body: imageFile,
            headers: { 'Content-Type': 'image/webp' },
          });
          if (!putRes.ok) throw new Error('Upload failed');
          await confirmGroupImage(group.group_id, key);
        } catch (err) {
          setImageError(
            getApiErrorMessage(
              err,
              'הקבוצה נוצרה, אך העלאת התמונה נכשלה. ניתן לעדכן תמונה בהגדרות הקבוצה.'
            )
          );
        }
      }
      setCreatedGroup({ inviteCode: group.invite_code, name: group.name });
      await refreshGroups();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'יצירת הקבוצה נכשלה.'));
    } finally {
      setSubmitting(false);
    }
  };

  const inviteUrl =
    createdGroup && typeof window !== 'undefined'
      ? `${window.location.origin}/join/${createdGroup.inviteCode}`
      : '';

  const handleCopy = async () => {
    if (!inviteUrl) return;
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const message = (err as Error)?.message || 'העתקה נכשלה. נסה שוב.';
      setCopyError(message);
    }
  };

  if (createdGroup) {
    return (
      <div className={styles.page}>
        <h1 className={styles.pageTitle}>הקבוצה נוצרה</h1>
        {imageError && (
          <p className={styles.imageWarn} role="alert">
            {imageError}
          </p>
        )}
        <div className={styles.successSection}>
          <div className={styles.successTitle}>הזמן חברים עם הקישור:</div>
          <div className={styles.inviteRow}>
            <input type="text" className={styles.inviteInput} value={inviteUrl} readOnly />
            <button
              type="button"
              className={`${styles.btn} ${styles.btnPrimary} ${styles.btnCopy} ${copied ? styles.btnCopySuccess : ''}`}
              onClick={handleCopy}
            >
              {copied ? '✓ הועתק!' : 'העתק'}
            </button>
          </div>
          {copyError ? (
            <ErrorBanner message={copyError} variant="compact" className={styles.inviteError} />
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>צור קבוצה</h1>
      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}
      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.label} htmlFor="group-name">
          שם הקבוצה
        </label>
        <input
          id="group-name"
          type="text"
          className={styles.input}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="למשל: נסיעות לתל אביב"
          required
        />
        <label className={styles.label} htmlFor="group-desc">
          תיאור (אופציונלי, עד {DESCRIPTION_MAX} תווים)
        </label>
        <textarea
          id="group-desc"
          className={styles.textarea}
          value={description}
          onChange={(e) => setDescription(e.target.value.slice(0, DESCRIPTION_MAX))}
          placeholder="תיאור קצר של הקבוצה"
          rows={3}
        />
        <span className={styles.charCount}>{description.length}/{DESCRIPTION_MAX}</span>
        <div
          className={styles.avatarUpload}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          aria-label="הוסף תמונה לקבוצה"
        >
          {previewUrl ? (
            <img src={previewUrl} className={styles.avatarPreview} alt="תצוגה מקדימה" />
          ) : (
            <div className={styles.avatarPlaceholder}>
              <Camera size={28} color="#9CA3AF" />
              <span>הוסף תמונה</span>
            </div>
          )}
          <div className={styles.avatarOverlay}>
            <Camera size={20} color="white" />
          </div>
          <input
            type="file"
            ref={fileInputRef}
            accept="image/*"
            className={styles.hiddenFileInput}
            onChange={handleImageChange}
          />
        </div>
        <LoadingButton
          type="submit"
          className={`${styles.btn} ${styles.btnPrimary}`}
          loading={submitting}
          loadingLabel="יוצר..."
        >
          צור קבוצה
        </LoadingButton>
      </form>
    </div>
  );
}
