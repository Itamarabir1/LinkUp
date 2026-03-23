import { useEffect, useMemo, useRef, useState } from 'react';
import { confirmGroupImage, getGroupImageUploadUrl, updateGroup } from '../../api/groups';
import type { Group } from '../../types/api';
import { getApiErrorMessage } from '../../utils/apiError';
import { GROUP_AVATAR_COLORS } from './groupManage.constants';

/**
 * כותרת דף ניהול קבוצה: אווטאר/תמונה, עריכת שם ותיאור.
 */
export function useGroupManageHeader(
  groupId: string | undefined,
  group: Group | null,
  isAdmin: boolean,
  refreshGroups: () => Promise<void>,
  setError: (message: string) => void
) {
  const [, setHeaderImageFile] = useState<File | null>(null);
  const [headerPreviewUrl, setHeaderPreviewUrl] = useState<string | null>(null);
  const [headerSaving, setHeaderSaving] = useState(false);
  const headerFileInputRef = useRef<HTMLInputElement>(null);

  const [editNameValue, setEditNameValue] = useState('');
  const [editDescriptionValue, setEditDescriptionValue] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [isEditingDesc, setIsEditingDesc] = useState(false);

  useEffect(() => {
    if (group) setEditNameValue(group.name);
  }, [group]);

  useEffect(() => {
    if (group) setEditDescriptionValue(group.description ?? '');
  }, [group]);

  const groupAvatarColor = useMemo(
    () =>
      group != null
        ? GROUP_AVATAR_COLORS[Math.abs(group.name.length) % GROUP_AVATAR_COLORS.length]
        : GROUP_AVATAR_COLORS[0],
    [group]
  );

  const handleAvatarClick = () => {
    if (!isAdmin) return;
    headerFileInputRef.current?.click();
  };

  const handleHeaderImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    e.target.value = '';
    if (!groupId) return;
    if (headerPreviewUrl) URL.revokeObjectURL(headerPreviewUrl);
    if (!file) {
      setHeaderPreviewUrl(null);
      setHeaderImageFile(null);
      return;
    }
    const preview = URL.createObjectURL(file);
    setHeaderPreviewUrl(preview);
    setHeaderImageFile(file);
    setHeaderSaving(true);
    setError('');
    try {
      const { upload_url, key } = await getGroupImageUploadUrl(groupId);
      await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': 'image/webp' },
      });
      await confirmGroupImage(groupId, key);
      await refreshGroups();
    } catch (err) {
      setError(getApiErrorMessage(err, 'שמירת השינויים נכשלה'));
    } finally {
      setHeaderSaving(false);
    }
  };

  const handleNameSave = async () => {
    if (!groupId || !group) return;
    const nameTrimmed = editNameValue.trim();
    if (!nameTrimmed || nameTrimmed === group.name) {
      setIsEditingName(false);
      setEditNameValue(group.name);
      return;
    }
    setHeaderSaving(true);
    setError('');
    try {
      await updateGroup(groupId, { name: nameTrimmed });
      await refreshGroups();
      setIsEditingName(false);
    } catch (err) {
      setError(getApiErrorMessage(err, 'שמירת השינויים נכשלה'));
    } finally {
      setHeaderSaving(false);
    }
  };

  const handleDescSave = async () => {
    if (!groupId) return;
    setHeaderSaving(true);
    setError('');
    try {
      await updateGroup(groupId, {
        description: editDescriptionValue.slice(0, 500) || undefined,
      });
      await refreshGroups();
      setIsEditingDesc(false);
    } catch (err) {
      setError(getApiErrorMessage(err, 'שמירת השינויים נכשלה'));
    } finally {
      setHeaderSaving(false);
    }
  };

  return {
    editNameValue,
    setEditNameValue,
    editDescriptionValue,
    setEditDescriptionValue,
    isEditingName,
    setIsEditingName,
    isEditingDesc,
    setIsEditingDesc,
    headerPreviewUrl,
    headerSaving,
    headerFileInputRef,
    groupAvatarColor,
    handleAvatarClick,
    handleHeaderImageChange,
    handleNameSave,
    handleDescSave,
  };
}
