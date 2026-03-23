import { useRef, useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { confirmAvatar, deleteMyAvatar, getAvatarUploadUrl } from '../api/users';
import { compressImage } from '../utils/imageUtils';
import { getApiErrorMessage } from '../utils/apiError';

export const ACCEPT_AVATAR = 'image/jpeg,image/png,image/webp';
export const MAX_SIZE_MB = 5;

export function useProfile() {
  const { user, logout, refreshUser } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prevAvatarUrlRef = useRef<string | null | undefined>(null);
  const avatarCacheBusterRef = useRef<number>(0);
  const [uploading, setUploading] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState('');
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarExpanded, setAvatarExpanded] = useState(false);
  const [avatarLoadError, setAvatarLoadError] = useState(false);

  const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`גודל מקסימלי ${MAX_SIZE_MB}MB`);
      return;
    }
    const ok = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type);
    if (!ok) {
      setError('סוג קובץ: JPEG, PNG או WebP בלבד');
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
      URL.revokeObjectURL(newPreviewUrl);
      setAvatarPreview(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'העלאת תמונה נכשלה'));
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
      setError(getApiErrorMessage(err, 'הסרת תמונה נכשלה'));
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
    : profileAvatarUrl
      ? `${encodeURI(profileAvatarUrl)}${profileAvatarUrl.includes('?') ? '&' : '?'}_v=${avatarCacheBusterRef.current}`
      : '';

  useEffect(() => {
    const currentUrl = profileAvatarUrl ?? null;
    if (prevAvatarUrlRef.current !== currentUrl) {
      prevAvatarUrlRef.current = currentUrl;
      avatarCacheBusterRef.current = Date.now();
      setAvatarLoadError(false);
    }
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
