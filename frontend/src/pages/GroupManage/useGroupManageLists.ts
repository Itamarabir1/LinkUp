import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect } from 'react';
import { getGroupMembers, getGroupRides } from '../../api/groups';
import { qk } from '../../api/queryKeys';
import type { GroupTab } from './groupManage.types';

export function useGroupManageLists(
  groupId: string | undefined,
  activeTab: GroupTab,
  refreshGroups: () => Promise<void>,
) {
  const queryClient = useQueryClient();

  const {
    data: members = [],
    isLoading: loadingMembers,
  } = useQuery({
    queryKey: qk.groups.members(groupId!),
    queryFn: ({ signal }) => getGroupMembers(groupId!, { signal }),
    enabled: !!groupId,
  });

  const {
    data: ridesPage,
    isLoading: loadingRides,
  } = useQuery({
    queryKey: qk.groups.rides(groupId!),
    queryFn: ({ signal }) => getGroupRides(groupId!, { limit: 20, signal }),
    enabled: !!groupId && activeTab === 'rides',
  });

  const rides = Array.isArray(ridesPage?.rides) ? ridesPage.rides : [];

  useEffect(() => {
    void refreshGroups();
  }, [refreshGroups]);

  const loadMembers = useCallback(async () => {
    if (!groupId) return;
    await queryClient.invalidateQueries({ queryKey: qk.groups.members(groupId) });
  }, [groupId, queryClient]);

  const loadRides = useCallback(async () => {
    if (!groupId) return;
    await queryClient.invalidateQueries({ queryKey: qk.groups.rides(groupId) });
  }, [groupId, queryClient]);

  return {
    members,
    rides,
    loadingMembers,
    loadingRides,
    loadMembers,
    loadRides,
  };
}
