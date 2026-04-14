import { useCallback, useState } from 'react';
import type { Group } from '../../types/api';

/** Invite-link creation and clipboard copy flow. */
export function useGroupManageInvite(group: Group | null) {
  const [, setCopyInviteDone] = useState(false);
  const [copyInviteError, setCopyInviteError] = useState<string | null>(null);

  const inviteUrl =
    group && typeof window !== 'undefined'
      ? `${window.location.origin}/join/${group.invite_code}`
      : '';

  const handleCopyInvite = useCallback(async () => {
    if (!group || typeof window === 'undefined') return;
    const url = `${window.location.origin}/join/${group.invite_code}`;
    if (!url) return;
    setCopyInviteError(null);
    try {
      await navigator.clipboard.writeText(url);
      setCopyInviteDone(true);
      setTimeout(() => setCopyInviteDone(false), 2000);
    } catch (err) {
      const message = (err as Error)?.message || 'העתקה נכשלה. נסה שוב.';
      setCopyInviteError(message);
    }
  }, [group]);

  return {
    inviteUrl,
    copyInviteError,
    handleCopyInvite,
  };
}
