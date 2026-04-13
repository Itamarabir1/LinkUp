import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import { ACCEPT_AVATAR, useProfile } from './useProfile';
import styles from './Profile.module.css';

export default function Profile() {
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

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>פרופיל</h1>
      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}
      {user && (
        <div className={`${styles.card} ${styles.profileCard}`}>
          <div className={styles.profileAvatarBlock}>
            <div
              className={hasValidAvatar ? `${styles.profileAvatarWrap} ${styles.profileAvatarClickable}` : styles.profileAvatarWrap}
              onClick={() => hasValidAvatar && setAvatarExpanded(true)}
              role={hasValidAvatar ? 'button' : undefined}
              aria-label={hasValidAvatar ? 'הצג תמונה בהגדלה' : undefined}
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
              {uploading && <div className={styles.profileAvatarOverlay}>מתעדכן...</div>}
            </div>
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
                    loadingLabel="מעלה..."
                    disabled={removing}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    החלף תמונה
                  </LoadingButton>
                  <span className={styles.profileAvatarLinkSep}>·</span>
                  <LoadingButton
                    type="button"
                    className={`${styles.profileAvatarLink} ${styles.profileAvatarLinkMuted}`}
                    loading={removing}
                    loadingLabel="מסיר..."
                    disabled={uploading}
                    onClick={handleRemoveAvatar}
                  >
                    הסר תמונה
                  </LoadingButton>
                </>
              ) : (
                <LoadingButton
                  type="button"
                  className={styles.profileAvatarLink}
                  loading={uploading}
                  loadingLabel="מעלה..."
                  onClick={() => fileInputRef.current?.click()}
                >
                  העלאת תמונה
                </LoadingButton>
              )}
            </div>
          </div>

          <div className={styles.profileBody}>
            <div className={styles.profileRow}>
              <span className={styles.profileLabel}>שם</span>
              <span className={styles.profileValue}>
                {user.full_name || user.first_name || user.email}
              </span>
            </div>
            <div className={styles.profileRow}>
              <span className={styles.profileLabel}>אימייל</span>
              <span className={styles.profileValue}>{user.email}</span>
            </div>
            {user.phone_number && (
              <div className={styles.profileRow}>
                <span className={styles.profileLabel}>טלפון</span>
                <span className={styles.profileValue}>{user.phone_number}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {avatarExpanded && hasValidAvatar && avatarSrc && (
        <div
          className={styles.avatarModalBackdrop}
          onClick={() => setAvatarExpanded(false)}
          onKeyDown={(e) => e.key === 'Escape' && setAvatarExpanded(false)}
          role="button"
          tabIndex={0}
          aria-label="סגור"
        >
          <button
            type="button"
            className={styles.avatarModalClose}
            onClick={() => setAvatarExpanded(false)}
            aria-label="סגור"
          >
            ×
          </button>
          <img
            src={avatarSrc}
            alt="תמונת פרופיל"
            className={styles.avatarModalImg}
            onClick={(e) => e.stopPropagation()}
            onError={() => {
              setAvatarExpanded(false);
              handleAvatarImageError();
            }}
          />
        </div>
      )}

      <button type="button" className={`${styles.btn} ${styles.btnDanger}`} onClick={() => logout()}>
        התנתק
      </button>
    </div>
  );
}
