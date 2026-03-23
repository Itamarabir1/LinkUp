import { useState } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import { closeGroup, leaveGroup, promoteMember, removeMember } from '../../api/groups';
import type { Group } from '../../types/api';
import { getApiErrorMessage } from '../../utils/apiError';

export interface UseGroupManageMutationsParams {
  groupId: string | undefined;
  navigate: NavigateFunction;
  setActiveGroup: (g: Group | null) => void;
  setActiveChipId: (id: string) => void;
  refreshGroups: () => Promise<void>;
  loadMembers: () => Promise<void>;
  setError: (message: string) => void;
  setOpenDropdown: (id: string | null) => void;
}

/**
 * פעולות מוטציה בדף ניהול קבוצה: חברים, עזיבה וסגירה.
 */
export function useGroupManageMutations({
  groupId,
  navigate,
  setActiveGroup,
  setActiveChipId,
  refreshGroups,
  loadMembers,
  setError,
  setOpenDropdown,
}: UseGroupManageMutationsParams) {
  const [actionLoading, setActionLoading] = useState(false);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);

  const handleRemoveMember = async (userId: string) => {
    if (!groupId) return;
    setOpenDropdown(null);
    setActionLoading(true);
    setError('');
    try {
      await removeMember(groupId, userId);
      await loadMembers();
      await refreshGroups();
    } catch (err) {
      setError(getApiErrorMessage(err, 'הסרת החבר נכשלה'));
    } finally {
      setActionLoading(false);
    }
  };

  const handlePromoteMember = async (userId: string) => {
    if (!groupId) return;
    setOpenDropdown(null);
    setActionLoading(true);
    setError('');
    try {
      await promoteMember(groupId, userId);
      await loadMembers();
      await refreshGroups();
    } catch (err) {
      setError(getApiErrorMessage(err, 'העלאת החבר למנהל נכשלה'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeave = async () => {
    if (!groupId) return;
    setActionLoading(true);
    setError('');
    try {
      await leaveGroup(groupId);
      setConfirmLeave(false);
      setActiveGroup(null);
      setActiveChipId('all');
      await refreshGroups();
      navigate('/groups', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, 'עזיבת הקבוצה נכשלה'));
    } finally {
      setActionLoading(false);
    }
  };

  const handleClose = async () => {
    if (!groupId) return;
    setActionLoading(true);
    setError('');
    try {
      await closeGroup(groupId);
      setConfirmClose(false);
      setActiveGroup(null);
      setActiveChipId('all');
      await refreshGroups();
      navigate('/groups', { replace: true });
    } catch (err) {
      setError(getApiErrorMessage(err, 'סגירת הקבוצה נכשלה'));
    } finally {
      setActionLoading(false);
    }
  };

  return {
    actionLoading,
    confirmLeave,
    setConfirmLeave,
    confirmClose,
    setConfirmClose,
    handleRemoveMember,
    handlePromoteMember,
    handleLeave,
    handleClose,
  };
}
