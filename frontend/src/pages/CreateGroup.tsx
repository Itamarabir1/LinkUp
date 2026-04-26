import { Camera, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { ACCEPT_GROUP_IMAGE, DESCRIPTION_MAX, useCreateGroup } from './useCreateGroup';
import styles from './CreateGroup.module.css';

export default function CreateGroup() {
  const { t } = useTranslation(['groups', 'common']);
  const {
    name,
    setName,
    description,
    setDescription,
    previewUrl,
    submitting,
    error,
    imageError,
    createdGroup,
    inviteUrl,
    copied,
    copyError,
    fileInputRef,
    handleImageChange,
    handleSubmit,
    handleCopy,
  } = useCreateGroup();

  /* ── Success state ── */
  if (createdGroup) {
    return (
      <div className={styles.page}>
        <div className={styles.inner}>
          {imageError && (
            <p className={styles.imageWarn} role="alert">{imageError}</p>
          )}
          <div className={styles.successCard}>
            <div className={styles.successAvatar}>{createdGroup.avatarLetter}</div>
            <p className={styles.successTitle}>{t('groups:createSuccess')}</p>
            <p className={styles.successSub}>
              {t('groups:shareInvite', { name: '' })}<strong>{createdGroup.name}</strong>
            </p>
            <div className={styles.inviteBox}>
              <div className={styles.inviteLabel}>{t('groups:joinLink')}</div>
              <div className={styles.inviteUrl}>{inviteUrl}</div>
            </div>
            {copyError && (
              <ErrorBanner
                message={copyError}
                variant="compact"
                className={styles.inviteError}
              />
            )}
            <button
              type="button"
              className={`${styles.btnCopy} ${copied ? styles.btnCopySuccess : ''}`}
              onClick={handleCopy}
            >
              {copied ? (
                <><Check size={14} strokeWidth={2.5} /> {t('common:copied')}</>
              ) : (
                <><Copy size={14} strokeWidth={2} /> {t('groups:copyLink')}</>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* ── Create form ── */
  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <h1 className={styles.pageTitle}>{t('groups:createGroup')}</h1>
        <div className={styles.card}>
          {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

          {/* Avatar upload */}
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
            aria-label={t('groups:createGroup')}
          >
            {previewUrl ? (
              <img
                src={previewUrl}
                className={styles.avatarPreview}
                alt={t('rides:previewButton')}
                loading="lazy"
              />
            ) : (
              <div className={styles.avatarPlaceholder}>
                <Camera size={24} strokeWidth={1.5} />
                <span>{t('profile:profileTitle')}</span>
              </div>
            )}
            <div className={styles.avatarOverlay}>
              <Camera size={18} color="white" />
            </div>
            <input
              type="file"
              ref={fileInputRef}
              accept={ACCEPT_GROUP_IMAGE}
              className={styles.hiddenFileInput}
              onChange={handleImageChange}
            />
          </div>

          <form className={styles.form} onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label className={styles.fieldLabel} htmlFor="group-name">
                {t('groups:groupName')}
              </label>
              <input
                id="group-name"
                type="text"
                className={styles.fieldInput}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('groups:groupName')}
                required
                autoComplete="off"
              />
            </div>

            <div className={styles.field}>
              <label className={styles.fieldLabel} htmlFor="group-desc">
                {t('groups:description')}{' '}
                <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>
                  ({t('common:or')})
                </span>
              </label>
              <textarea
                id="group-desc"
                className={styles.fieldTextarea}
                value={description}
                onChange={(e) => setDescription(e.target.value.slice(0, DESCRIPTION_MAX))}
                placeholder={t('groups:description')}
                rows={3}
              />
              <span className={styles.charCount}>
                {description.length} / {DESCRIPTION_MAX}
              </span>
            </div>

            <LoadingButton
              type="submit"
              className={styles.btnPrimary}
              loading={submitting}
              loadingLabel={t('common:creating')}
            >
              {t('groups:createGroup')}
            </LoadingButton>
          </form>
        </div>
      </div>
    </div>
  );
}
