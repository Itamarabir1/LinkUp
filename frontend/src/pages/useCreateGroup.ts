import { useEffect, useRef, useState } from 'react';
import { createGroup, getGroupImageUploadUrl, confirmGroupImage } from '../api/groups';
import { useGroup } from '../context/GroupContext';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';

export const DESCRIPTION_MAX = 500;
export const ACCEPT_GROUP_IMAGE = 'image/*';

export interface CreatedGroupInfo {
  inviteCode: string;
  name: string;
  avatarLetter: string;
}

export function useCreateGroup() {
  const { refreshGroups } = useGroup();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [imageError, setImageError] = useState<string | null>(null);
  const [createdGroup, setCreatedGroup] = useState<CreatedGroupInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cleanup object URL on unmount or when previewUrl changes
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

      // Upload image if provided
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
            getApiErrorMessage(err, apiErr('err_group_image_partial'))
          );
        }
      }

      setCreatedGroup({
        inviteCode: group.invite_code,
        name: group.name,
        avatarLetter: group.name.charAt(0).toUpperCase(),
      });
      await refreshGroups();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_create_group')));
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
      setCopyError(getApiErrorMessage(err, apiErr('err_copy_clipboard')));
    }
  };

  return {
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
  };
}
