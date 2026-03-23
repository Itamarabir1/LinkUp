import { useCallback, useEffect, useState } from 'react';
import { getGroupMembers, getGroupRides } from '../../api/groups';
import type { GroupMember, Ride } from '../../types/api';
import { getApiErrorMessage } from '../../utils/apiError';
import type { GroupTab } from './groupManage.types';

/**
 * טעינת חברים ונסיעות לדף ניהול קבוצה (מופרד מ-useGroupManage לקריאות).
 */
export function useGroupManageLists(
  groupId: string | undefined,
  activeTab: GroupTab,
  refreshGroups: () => Promise<void>,
  setError: (message: string) => void
) {
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [rides, setRides] = useState<Ride[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [loadingRides, setLoadingRides] = useState(false);

  const loadMembers = useCallback(async () => {
    if (!groupId) return;
    setLoadingMembers(true);
    setError('');
    try {
      const list = await getGroupMembers(groupId);
      setMembers(list);
    } catch (err) {
      setError(getApiErrorMessage(err, 'טעינת חברי הקבוצה נכשלה'));
      setMembers([]);
    } finally {
      setLoadingMembers(false);
    }
  }, [groupId, setError]);

  const loadRides = useCallback(async () => {
    if (!groupId) return;
    setLoadingRides(true);
    setError('');
    try {
      const list = await getGroupRides(groupId);
      setRides(Array.isArray(list) ? list : []);
    } catch (err) {
      setError(getApiErrorMessage(err, 'טעינת נסיעות הקבוצה נכשלה'));
      setRides([]);
    } finally {
      setLoadingRides(false);
    }
  }, [groupId, setError]);

  useEffect(() => {
    void refreshGroups();
  }, [refreshGroups]);

  useEffect(() => {
    void loadMembers();
  }, [loadMembers]);

  useEffect(() => {
    if (activeTab === 'rides') void loadRides();
  }, [activeTab, loadRides]);

  return {
    members,
    rides,
    loadingMembers,
    loadingRides,
    loadMembers,
    loadRides,
  };
}
