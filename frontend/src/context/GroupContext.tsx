import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { Group } from '../types/api';
import { getMyGroups } from '../api/groups';
import { getApiErrorMessage } from '../utils/apiError';
import { useAuth } from './AuthContext';

type GroupContextValue = {
  activeGroup: Group | null;        // null = ציבורי — משמש ב־mutations (ניהול קבוצה)
  setActiveGroup: (g: Group | null) => void;
  /** פילטר משותף ל־MyRides / MyRequests: 'all' | 'public' | group_id */
  activeChipId: string;
  setActiveChipId: (id: string) => void;
  myGroups: Group[];
  isLoadingGroups: boolean;
  /** הודעת שגיאה אחרונה מטעינת קבוצות (ריק אם אין) */
  groupsError: string;
  refreshGroups: () => Promise<void>;
};

const GroupContext = createContext<GroupContextValue | null>(null);

export function GroupProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [activeGroup, setActiveGroupState] = useState<Group | null>(null);
  const [activeChipId, setActiveChipId] = useState<string>('all');
  const [myGroups, setMyGroups] = useState<Group[]>([]);
  const [isLoadingGroups, setIsLoadingGroups] = useState(false);
  const [groupsError, setGroupsError] = useState('');

  const refreshGroups = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsLoadingGroups(true);
    setGroupsError('');
    try {
      const groups = await getMyGroups();
      setMyGroups(groups);
    } catch (err) {
      setMyGroups([]);
      setGroupsError(getApiErrorMessage(err, 'טעינת הקבוצות נכשלה'));
    } finally {
      setIsLoadingGroups(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refreshGroups();
  }, [refreshGroups]);

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
