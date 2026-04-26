import React, { createContext, useContext, useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { Group } from '../types/api';
import { getMyGroups } from '../api/groups';
import { qk } from '../api/queryKeys';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { useAuth } from './AuthContext';

type GroupContextValue = {
  activeGroup: Group | null;        // null = public context; used in group-management mutations
  setActiveGroup: (g: Group | null) => void;
  /** Shared filter for MyRides / MyRequests: 'all' | 'public' | group_id. */
  activeChipId: string;
  setActiveChipId: (id: string) => void;
  myGroups: Group[];
  isLoadingGroups: boolean;
  /** Last groups-loading error message (empty when none). */
  groupsError: string;
  refreshGroups: () => Promise<void>;
};

const GroupContext = createContext<GroupContextValue | null>(null);

export function GroupProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [activeGroup, setActiveGroupState] = useState<Group | null>(null);
  const [activeChipId, setActiveChipId] = useState<string>('all');
  const {
    data: myGroups = [],
    isLoading: isLoadingGroups,
    error,
  } = useQuery({
    queryKey: qk.groups.list(),
    queryFn: getMyGroups,
    enabled: isAuthenticated,
    staleTime: 2 * 60_000,
  });
  const groupsError = error ? getApiErrorMessage(error, apiErr('err_load_groups')) : '';

  const refreshGroups = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: qk.groups.list() });
  }, [queryClient]);

  const setActiveGroup = (g: Group | null) => {
    setActiveGroupState(g);
  };

  return (
    <GroupContext.Provider
      value={{
        activeGroup,
        setActiveGroup,
        activeChipId,
        setActiveChipId,
        myGroups,
        isLoadingGroups,
        groupsError,
        refreshGroups,
      }}
    >
      {children}
    </GroupContext.Provider>
  );
}

export function useGroup() {
  const ctx = useContext(GroupContext);
  if (!ctx) throw new Error('useGroup must be used within GroupProvider');
  return ctx;
}
