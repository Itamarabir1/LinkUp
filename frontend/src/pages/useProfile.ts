import { useRef, useState, useEffect } from 'react';
import i18n from '../i18n';
import { useAuth } from '../context/AuthContext';
import { confirmAvatar, deleteMyAvatar, fetchCurrentUser, getAvatarUploadUrl } from '../api/users';
import { compressImage } from '../utils/imageUtils';
import { getApiErrorMessage } from '../utils/apiError';

export const ACCEPT_AVATAR = 'image/jpeg,image/png,image/webp';
export const MAX_SIZE_MB = 5;

export function useProfile() {
  const { user, logout, refreshUser } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState('');
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarExpanded, setAvatarExpanded] = useState(false);
  const [avatarLoadError, setAvatarLoadError] = useState(false);

  const waitForAvatarReady = async () => {
    // Poll short-term while worker finalizes staging -> final variants.
    for (let i = 0; i < 12; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      try {
        const { data } = await fetchCurrentUser();
        if (data.avatar_status === 'ready' && data.avatar_url_medium) {
          await refreshUser();
          return true;
        }
      } catch {
        // Ignore transient read errors while polling.
      }
    }
    return false;
  };

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(i18n.t('profile:maxImageSize', { size: MAX_SIZE_MB }));
      return;
    }
    const ok = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type);
    if (!ok) {
      setError(i18n.t('profile:allowedImageTypes'));
      return;
    }
    setError('');
    setAvatarLoadError(false);
    setUploading(true);
    if (avatarPreview) URL.revokeObjectURL(avatarPreview);
    const newPreviewUrl = URL.createObjectURL(file);
    setAvatarPreview(newPreviewUrl);
    try {
      const compressed = await compressImage(file, { maxWidth: 800, quality: 0.85 });
      const { data: uploadData } = await getAvatarUploadUrl();
      await fetch(uploadData.upload_url, {
        method: 'PUT',
        body: compressed,
        headers: { 'Content-Type': 'image/webp' },
      });
      await confirmAvatar(uploadData.staging_key);
      await refreshUser();
      const ready = await waitForAvatarReady();
      if (ready) {
        URL.revokeObjectURL(newPreviewUrl);
        setAvatarPreview(null);
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, i18n.t('profile:uploadFailed')));
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveAvatar = async () => {
    if (!user?.avatar_key && !(user as { avatar_url?: string })?.avatar_url) return;
    setError('');
    setRemoving(true);
    setAvatarLoadError(false);
    try {
      await deleteMyAvatar();
      await refreshUser();
      setTimeout(() => refreshUser(), 2000);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, i18n.t('profile:removeFailed')));
    } finally {
      setRemoving(false);
    }
  };

  const handleAvatarImageError = () => {
    setAvatarLoadError(true);
  };

  const profileAvatarUrl = (user as { avatar_url_medium?: string; avatar_url?: string })?.avatar_url_medium
    ?? (user as { avatar_url?: string })?.avatar_url;
  const hasValidAvatar = (profileAvatarUrl || avatarPreview) && !avatarLoadError;
  const avatarSrc = avatarPreview
    ? avatarPreview
    : profileAvatarUrl ?? '';

  useEffect(() => {
    setAvatarLoadError(false);
  }, [profileAvatarUrl]);

  return {
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
    ACCEPT_AVATAR,
  };
}
