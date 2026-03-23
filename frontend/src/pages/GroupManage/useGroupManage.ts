import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useGroup } from '../../context/GroupContext';
import { DATE_CHIP_ITEMS, GROUP_AVATAR_COLORS, MEMBERS_PREVIEW } from './groupManage.constants';
import type { GroupTab } from './groupManage.types';
import { isThisWeek, isToday, isTomorrow } from './groupManage.utils';
import { useGroupManageHeader } from './useGroupManageHeader';
import { useGroupManageInvite } from './useGroupManageInvite';
import { useGroupManageLists } from './useGroupManageLists';
import { useGroupManageMutations } from './useGroupManageMutations';

export function useGroupManage() {
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { myGroups, isLoadingGroups, refreshGroups, setActiveGroup, setActiveChipId } = useGroup();

  const group = useMemo(
    () => (groupId ? myGroups.find((g) => g.group_id === groupId) ?? null : null),
    [groupId, myGroups]
  );

  const isAdmin = !!(group && user?.user_id && group.admin_id === user.user_id);

  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<GroupTab>('rides');
  const {
    members,
    rides,
    loadingMembers,
    loadingRides,
    loadMembers,
  } = useGroupManageLists(groupId, activeTab, refreshGroups, setError);

  const [dateChip, setDateChip] = useState<string>('all');
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [membersModalOpen, setMembersModalOpen] = useState(false);
  const [membersSearch, setMembersSearch] = useState('');

  const header = useGroupManageHeader(groupId, group, isAdmin, refreshGroups, setError);
  const invite = useGroupManageInvite(group);
  const mutations = useGroupManageMutations({
    groupId,
    navigate,
    setActiveGroup,
    setActiveChipId,
    refreshGroups,
    loadMembers,
    setError,
    setOpenDropdown,
  });

  const filteredMembers = useMemo(
    () =>
      members.filter((m) =>
        (m.full_name ?? '').toLowerCase().includes(membersSearch.trim().toLowerCase())
      ),
    [members, membersSearch]
  );

  const displayedRides = useMemo(() => {
    return rides.filter((r) => {
      if (r.status === 'cancelled') return false;
      if (dateChip === 'all') return true;
      const d = new Date(r.departure_time);
      if (dateChip === 'today') return isToday(d);
      if (dateChip === 'tomorrow') return isTomorrow(d);
      if (dateChip === 'week') return isThisWeek(d);
      return true;
    });
  }, [rides, dateChip]);

  return {
    groupId,
    navigate,
    user,
    group,
    isLoadingGroups,
    isAdmin,
    members,
    rides,
    loadingMembers,
    loadingRides,
    error,
    activeTab,
    setActiveTab,
    dateChip,
    setDateChip,
    ...header,
    ...invite,
    ...mutations,
    openDropdown,
    setOpenDropdown,
    membersModalOpen,
    setMembersModalOpen,
    membersSearch,
    setMembersSearch,
    filteredMembers,
    displayedRides,
    dateChipItems: DATE_CHIP_ITEMS,
    membersPreview: MEMBERS_PREVIEW,
    avatarColors: GROUP_AVATAR_COLORS,
  };
}

export type GroupManageViewModel = ReturnType<typeof useGroupManage>;
