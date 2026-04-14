import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { ACCEPT_AVATAR, useProfile } from './useProfile';
import styles from './Profile.module.css';

export default function Profile() {
  const { t } = useTranslation(['profile', 'auth', 'common']);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const {
    user,
    logout,
    fileInputRef,
    uploading,
    removing,
    error,
    avatarExpanded,
    setAvatarExpanded,
    hasValidAvatar,
    avatarSrc,
    handleAvatarChange,
    handleRemoveAvatar,
    handleAvatarImageError,
  } = useProfile();

  useEffect(() => {
    if (avatarExpanded) closeButtonRef.current?.focus();
  }, [avatarExpanded]);

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <h1 className={styles.pageTitle}>{t('profile:profileTitle')}</h1>
        {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

        {user && (
          <>
            <div className={styles.avatarCard}>
              <div className={styles.avatarHeader}>
                <div
                  className={
                    hasValidAvatar
                      ? `${styles.profileAvatarWrap} ${styles.profileAvatarClickable}`
                      : styles.profileAvatarWrap
                  }
                  onClick={() => hasValidAvatar && setAvatarExpanded(true)}
                  role={hasValidAvatar ? 'button' : undefined}
                  aria-label={hasValidAvatar ? t('profile:viewImageExpanded') : undefined}
                >
                  {hasValidAvatar ? (
                    <img
                      src={avatarSrc}
                      alt=""
                      className={styles.profileAvatarImg}
                      onError={handleAvatarImageError}
                    />
                  ) : (
                    <div className={styles.profileAvatarPlaceholder}>
                      {(user.full_name || user.email || '?').charAt(0).toUpperCase()}
                    </div>
                  )}
                  {uploading ? (
                    <div className={styles.profileAvatarOverlay}>{t('profile:avatarOverlayUpdating')}</div>
                  ) : null}
                </div>

                <div className={styles.avatarDisplayName}>
                  {user.full_name || user.first_name || user.email}
                </div>
                <div className={styles.avatarDisplayEmail}>{user.email}</div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPT_AVATAR}
                  onChange={handleAvatarChange}
                  className={styles.hiddenFileInput}
                  disabled={uploading}
                />

                <div className={styles.profileAvatarLinks}>
                  {hasValidAvatar ? (
                    <>
                      <LoadingButton
                        type="button"
                        className={styles.profileAvatarLink}
                        loading={uploading}
                        loadingLabel={t('profile:uploadingImage')}
                        disabled={removing}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        {t('profile:replaceImage')}
                      </LoadingButton>
                      <LoadingButton
                        type="button"
                        className={`${styles.profileAvatarLink} ${styles.profileAvatarLinkMuted}`}
                        loading={removing}
                        loadingLabel={t('profile:removingImage')}
                        disabled={uploading}
                        onClick={handleRemoveAvatar}
                      >
                        {t('profile:removeImage')}
                      </LoadingButton>
                    </>
                  ) : (
                    <LoadingButton
                      type="button"
                      className={styles.profileAvatarLink}
                      loading={uploading}
                      loadingLabel={t('profile:uploadingImage')}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {t('profile:uploadImage')}
                    </LoadingButton>
                  )}
                </div>
              </div>
            </div>

            <div className={styles.infoCard}>
              <div className={styles.profileRow}>
                <span className={styles.profileLabel}>{t('profile:name')}</span>
                <span className={styles.profileValue}>
                  {user.full_name || user.first_name || user.email}
                </span>
              </div>
              <div className={styles.profileRow}>
                <span className={styles.profileLabel}>{t('profile:email')}</span>
                <span className={styles.profileValue}>{user.email}</span>
              </div>
              {user.phone_number ? (
                <div className={styles.profileRow}>
                  <span className={styles.profileLabel}>{t('profile:phone')}</span>
                  <span className={`${styles.profileValue} ${styles.profileValueLtr}`}>
                    {user.phone_number}
                  </span>
                </div>
              ) : null}
            </div>
          </>
        )}

        <button type="button" className={styles.btnDanger} onClick={() => logout()}>
          {t('auth:logout')}
        </button>
      </div>

      {avatarExpanded && hasValidAvatar && avatarSrc ? (
        <div
          className={styles.avatarModalBackdrop}
          onClick={() => setAvatarExpanded(false)}
          onKeyDown={(e) => e.key === 'Escape' && setAvatarExpanded(false)}
          role="dialog"
          aria-modal="true"
          aria-label={t('profile:profileImageExpanded')}
        >
          <button
            ref={closeButtonRef}
            type="button"
            className={styles.avatarModalClose}
            onClick={() => setAvatarExpanded(false)}
            aria-label={t('common:close')}
          >
            <X size={18} strokeWidth={2} />
          </button>
          <img
            src={avatarSrc}
            alt={t('profile:profileImage')}
            className={styles.avatarModalImg}
            onClick={(e) => e.stopPropagation()}
            onError={() => {
              setAvatarExpanded(false);
              handleAvatarImageError();
            }}
          />
        </div>
      ) : null}
    </div>
  );
}
