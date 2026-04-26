import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { createGroup, getGroupImageUploadUrl, confirmGroupImage } from '../api/groups';
import { qk } from '../api/queryKeys';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';

export const DESCRIPTION_MAX = 500;
export const ACCEPT_GROUP_IMAGE = 'image/*';

export interface CreatedGroupInfo {
  inviteCode: string;
  name: string;
  avatarLetter: string;
}

const createGroupSchema = z.object({
  name: z.string().min(1),
  description: z.string().max(DESCRIPTION_MAX).optional(),
});

type CreateGroupForm = z.infer<typeof createGroupSchema>;

export function useCreateGroup() {
  const queryClient = useQueryClient();
  const {
    watch,
    setValue,
    handleSubmit: rhfHandleSubmit,
    formState: { isSubmitting },
  } = useForm<CreateGroupForm>({
    resolver: zodResolver(createGroupSchema),
    defaultValues: { name: '', description: '' },
  });
  const name = watch('name') ?? '';
  const description = watch('description') ?? '';
  const setName = useCallback((v: string) => {
    setValue('name', v, { shouldDirty: true, shouldTouch: true });
  }, [setValue]);
  const setDescription = useCallback((v: string) => {
    setValue('description', v, { shouldDirty: true, shouldTouch: true });
  }, [setValue]);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [imageError, setImageError] = useState<string | null>(null);
  const [createdGroup, setCreatedGroup] = useState<CreatedGroupInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const createMutation = useMutation({
    mutationKey: ['groups', 'create'] as const,
    mutationFn: async (payload: { name: string; description?: string }) => createGroup(payload),
    onSuccess: (group) => {
      void queryClient.invalidateQueries({ queryKey: qk.groups.list() });
      setCreatedGroup({
        inviteCode: group.invite_code,
        name: group.name,
        avatarLetter: group.name.charAt(0).toUpperCase(),
      });
    },
    onError: (err) => {
      setError(getApiErrorMessage(err, apiErr('err_create_group')));
    },
  });

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

  const onSubmit = rhfHandleSubmit(async (formData) => {
    const trimmed = formData.name.trim();
    if (!trimmed) return;
    setError('');
    setImageError(null);
    try {
      const group = await createMutation.mutateAsync({
        name: trimmed,
        description: (formData.description ?? '').trim().slice(0, DESCRIPTION_MAX) || undefined,
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

    } catch {
      // API error is handled by mutation onError.
    }
  });

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
    submitting: isSubmitting,
    error,
    imageError,
    createdGroup,
    inviteUrl,
    copied,
    copyError,
    fileInputRef,
    handleImageChange,
    handleSubmit: onSubmit,
    handleCopy,
  };
}
