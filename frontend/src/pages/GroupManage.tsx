import { useCallback, useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Search, Plus, Settings, MoreVertical, Crown, Pencil, Camera } from 'lucide-react';
import {
  getGroupMembers,
  removeMember,
  promoteMember,
  leaveGroup,
  closeGroup,
  updateGroup,
  getGroupRides,
  getGroupImageUploadUrl,
  confirmGroupImage,
} from '../api/groups';
import { useAuth } from '../context/AuthContext';
import { useGroup } from '../context/GroupContext';
import type { GroupMember as GroupMemberType } from '../types/api';
import type { Ride } from '../types/api';
import { formatRideDate } from '../utils/date';
import Chips, { type ChipItem } from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import styles from './GroupManage.module.css';

const AVATAR_COLORS = ['#6366f1', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0ea5e9'];

function getStatusLabel(r: Ride): string {
  if (r.status === 'cancelled') return 'בוטלה';
  const seats = r.available_seats ?? 0;
  if (seats <= 0) return 'מלא';
  if (seats === 1) return '1 מקום';
  return `${seats} מקומות`;
}

function isToday(d: Date): boolean {
  const today = new Date();
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  );
}

function isTomorrow(d: Date): boolean {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return (
    d.getFullYear() === tomorrow.getFullYear() &&
    d.getMonth() === tomorrow.getMonth() &&
    d.getDate() === tomorrow.getDate()
  );
}

function isThisWeek(d: Date): boolean {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  const t = d.getTime();
  return t >= start.getTime() && t < end.getTime();
}

type GroupTab = 'rides' | 'members' | 'settings';

export default function GroupManage() {
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { myGroups, isLoadingGroups, refreshGroups, setActiveGroup } = useGroup();
  const [members, setMembers] = useState<GroupMemberType[]>([]);
  const [rides, setRides] = useState<Ride[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [loadingRides, setLoadingRides] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<GroupTab>('rides');
  const [dateChip, setDateChip] = useState<string>('all');
  const [editNameValue, setEditNameValue] = useState('');
  const [, setCopyInviteDone] = useState(false);
  const [copyInviteError, setCopyInviteError] = useState<string | null>(null);
  const [confirmLeave, setConfirmLeave] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [membersModalOpen, setMembersModalOpen] = useState(false);
  const [membersSearch, setMembersSearch] = useState('');
  const [editDescriptionValue, setEditDescriptionValue] = useState('');
  const [isEditingName, setIsEditingName] = useState(false);
  const [isEditingDesc, setIsEditingDesc] = useState(false);
  const [, setHeaderImageFile] = useState<File | null>(null);
  const [headerPreviewUrl, setHeaderPreviewUrl] = useState<string | null>(null);
  const [headerSaving, setHeaderSaving] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const headerFileInputRef = useRef<HTMLInputElement>(null);

  const group = groupId ? (myGroups.find((g) => g.group_id === groupId) ?? null) : null;
  const MEMBERS_PREVIEW = 8;
  const filteredMembers = members.filter((m) =>
    (m.full_name ?? '').toLowerCase().includes(membersSearch.trim().toLowerCase())
  );

  const dateChipItems: ChipItem[] = [
    { id: 'all', label: 'הכל' },
    { id: 'today', label: 'היום' },
    { id: 'tomorrow', label: 'מחר' },
    { id: 'week', label: 'השבוע' },
  ];

  const displayedRides = rides.filter((r) => {
    if (r.status === 'cancelled') return false;
    if (dateChip === 'all') return true;
    const d = new Date(r.departure_time);
    if (dateChip === 'today') return isToday(d);
    if (dateChip === 'tomorrow') return isTomorrow(d);
    if (dateChip === 'week') return isThisWeek(d);
    return true;
  });

  const loadMembers = useCallback(async () => {
    if (!groupId) return;
    setLoadingMembers(true);
    setError('');
    try {
      const list = await getGroupMembers(groupId);
      setMembers(list);
    } catch {
      setError('טעינת חברי הקבוצה נכשלה');
      setMembers([]);
    } finally {
      setLoadingMembers(false);
    }
  }, [groupId]);

  const loadRides = useCallback(async () => {
    if (!groupId) return;
    setLoadingRides(true);
    setError('');
    try {
      const list = await getGroupRides(groupId);
      setRides(Array.isArray(list) ? list : []);
    } catch {
      setError('טעינת נסיעות הקבוצה נכשלה');
      setRides([]);
    } finally {
      setLoadingRides(false);
    }
  }, [groupId]);

  useEffect(() => {
    refreshGroups();
  }, [refreshGroups]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  useEffect(() => {
    if (activeTab === 'rides') loadRides();
  }, [activeTab, loadRides]);

  useEffect(() => {
    if (group) setEditNameValue(group.name);
  }, [group]);

  useEffect(() => {
    if (group) setEditDescriptionValue(group.description ?? '');
  }, [group]);

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
    } catch {
      setError('שמירת השינויים נכשלה');
    } finally {
      setHeaderSaving(false);
    }
  };

  const handleNameSave = async () => {
    if (!groupId) return;
    if (!group) return;
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
    } catch {
      setError('שמירת השינויים נכשלה');
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
    } catch {
      setError('שמירת השינויים נכשלה');
    } finally {
      setHeaderSaving(false);
    }
  };

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (!groupId) {
    return (
      <div className={styles.page}>
        <p className={styles.pageError}>חסר מזהה קבוצה.</p>
      </div>
    );
  }

  if (!isLoadingGroups && !group) {
    return (
      <div className={styles.page}>
        <p className={styles.pageError}>הקבוצה לא נמצאה או שאין לך גישה אליה.</p>
      </div>
    );
  }

  if (!group) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>טוען...</div>
      </div>
    );
  }

  const isAdmin = group.admin_id === user?.user_id;
  const inviteUrl =
    typeof window !== 'undefined' ? `${window.location.origin}/join/${group.invite_code}` : '';

  const handleCopyInvite = async () => {
    if (!inviteUrl) return;
    setCopyInviteError(null);
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopyInviteDone(true);
      setTimeout(() => setCopyInviteDone(false), 2000);
    } catch (err) {
      const message = (err as Error)?.message || 'העתקה נכשלה. נסה שוב.';
      setCopyInviteError(message);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    setOpenDropdown(null);
    setActionLoading(true);
    setError('');
    try {
      await removeMember(groupId, userId);
      await loadMembers();
      await refreshGroups();
    } catch {
      setError('הסרת החבר נכשלה');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePromoteMember = async (userId: string) => {
    setOpenDropdown(null);
    setActionLoading(true);
    setError('');
    try {
      await promoteMember(groupId, userId);
      await loadMembers();
      await refreshGroups();
    } catch {
      setError('העלאת החבר למנהל נכשלה');
    } finally {
      setActionLoading(false);
    }
  };

  const handleLeave = async () => {
    setActionLoading(true);
    setError('');
    try {
      await leaveGroup(groupId);
      setConfirmLeave(false);
      setActiveGroup(null);
      await refreshGroups();
      navigate('/groups', { replace: true });
    } catch {
      setError('עזיבת הקבוצה נכשלה');
    } finally {
      setActionLoading(false);
    }
  };

  const handleClose = async () => {
    setActionLoading(true);
    setError('');
    try {
      await closeGroup(groupId);
      setConfirmClose(false);
      setActiveGroup(null);
      await refreshGroups();
      navigate('/groups', { replace: true });
    } catch {
      setError('סגירת הקבוצה נכשלה');
    } finally {
      setActionLoading(false);
    }
  };

  const groupAvatarColor = AVATAR_COLORS[Math.abs(group.name.length) % AVATAR_COLORS.length];

  return (
    <div className={styles.page}>
      <header className={styles.groupHeader}>
        {isAdmin && (
          <button
            type="button"
            className={styles.headerSettingsBtn}
            onClick={() => setActiveTab('settings')}
            title="הגדרות קבוצה"
          >
            <Settings size={18} />
          </button>
        )}

        <input
          ref={headerFileInputRef}
          type="file"
          accept="image/*"
          className={styles.hiddenInput}
          onChange={handleHeaderImageChange}
        />

        <button
          type="button"
          className={styles.headerAvatarWrap}
          onClick={handleAvatarClick}
          disabled={headerSaving || !isAdmin}
        >
          {group.avatar_url && !headerPreviewUrl ? (
            <img src={group.avatar_url} alt={group.name} className={styles.headerAvatarImg} />
          ) : headerPreviewUrl ? (
            <img src={headerPreviewUrl} alt={group.name} className={styles.headerAvatarImg} />
          ) : (
            <div className={styles.headerAvatar} style={{ backgroundColor: groupAvatarColor }}>
              {group.name.charAt(0).toUpperCase()}
            </div>
          )}
          {isAdmin && (
            <span className={styles.headerAvatarOverlay}>
              <Camera size={20} />
            </span>
          )}
        </button>

        {!isEditingName ? (
          <div className={styles.nameRow}>
            <h1 className={styles.headerName}>{group.name}</h1>
            {isAdmin && (
              <button
                type="button"
                className={styles.editIconBtn}
                onClick={() => setIsEditingName(true)}
                aria-label="ערוך שם קבוצה"
              >
                <Pencil size={14} />
              </button>
            )}
          </div>
        ) : (
          <div className={styles.inlineEditRow}>
            <input
              type="text"
              className={styles.inlineInput}
              value={editNameValue}
              onChange={(e) => setEditNameValue(e.target.value)}
              maxLength={50}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  void handleNameSave();
                }
                if (e.key === 'Escape') {
                  setEditNameValue(group.name);
                  setIsEditingName(false);
                }
              }}
              disabled={headerSaving}
            />
            <button
              type="button"
              className={styles.inlineSave}
              onClick={() => void handleNameSave()}
              disabled={headerSaving}
            >
              ✓
            </button>
            <button
              type="button"
              className={styles.inlineCancel}
              onClick={() => {
                setEditNameValue(group.name);
                setIsEditingName(false);
              }}
              disabled={headerSaving}
            >
              ✕
            </button>
          </div>
        )}

        {!isEditingDesc ? (
          <div className={styles.descRow}>
            <p className={styles.headerDescription}>
              {group.description || (isAdmin ? 'הוסף תיאור...' : '')}
            </p>
            {isAdmin && (
              <button
                type="button"
                className={styles.editIconBtn}
                onClick={() => setIsEditingDesc(true)}
                aria-label="ערוך תיאור קבוצה"
              >
                <Pencil size={14} />
              </button>
            )}
          </div>
        ) : (
          <div className={styles.inlineEditCol}>
            <textarea
              className={styles.inlineTextarea}
              value={editDescriptionValue}
              onChange={(e) => setEditDescriptionValue(e.target.value.slice(0, 500))}
              rows={2}
              autoFocus
              disabled={headerSaving}
            />
            <div className={styles.inlineActions}>
              <button
                type="button"
                className={styles.inlineSave}
                onClick={() => void handleDescSave()}
                disabled={headerSaving}
              >
                שמור
              </button>
              <button
                type="button"
                className={styles.inlineCancel}
                onClick={() => {
                  setEditDescriptionValue(group.description ?? '');
                  setIsEditingDesc(false);
                }}
                disabled={headerSaving}
              >
                ביטול
              </button>
            </div>
          </div>
        )}

        <p className={styles.groupMeta}>
          👥 {group.member_count ?? members.length} חברים
          {group.is_active === false && ' · לא פעילה'}
        </p>

        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.headerBtn}
            onClick={() => navigate('/search')}
            title="חפש בקבוצה"
          >
            <Search size={18} />
            חפש נסיעה בקבוצה
          </button>
          <button
            type="button"
            className={styles.headerBtnPrimary}
            onClick={() => navigate('/create-ride', { state: { groupId } })}
            title="הצע נסיעה לקבוצה"
          >
            <Plus size={18} />
            הצע נסיעה לקבוצה
          </button>
        </div>
      </header>

      <div role="tablist" className={styles.tabs}>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'rides'}
          className={activeTab === 'rides' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('rides')}
        >
          נסיעות
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'members'}
          className={activeTab === 'members' ? styles.tabActive : styles.tab}
          onClick={() => setActiveTab('members')}
        >
          חברים
        </button>
        {isAdmin && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'settings'}
            className={activeTab === 'settings' ? styles.tabActive : styles.tab}
            onClick={() => setActiveTab('settings')}
          >
            הגדרות
          </button>
        )}
      </div>

      {error && <p className={styles.pageError}>{error}</p>}

      {activeTab === 'rides' && (
        <>
          <Chips items={dateChipItems} activeId={dateChip} onChange={setDateChip} />
          {loadingRides ? (
            <div className={styles.pageLoading}>טוען נסיעות...</div>
          ) : displayedRides.length === 0 ? (
            <div className={styles.emptyState}>
              <p className={styles.emptyText}>אין נסיעות בקבוצה בתקופה הזו.</p>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={() => navigate('/create-ride', { state: { groupId } })}
              >
                <Plus size={14} />
                הצע נסיעה
              </button>
            </div>
          ) : (
            <div className={styles.ridesGrid}>
              {displayedRides.map((r) => (
                <RideCard
                  key={r.ride_id}
                  route={`${r.origin_name ?? '?'} ← ${r.destination_name ?? '?'}`}
                  time={formatRideDate(r.departure_time)}
                  status={getStatusLabel(r)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'members' && (
        <>
          {loadingMembers ? (
            <div className={styles.pageLoading}>טוען חברים...</div>
          ) : (
            <>
              <p className={styles.membersCountHeader}>
                {members.length} חברים
              </p>
              <ul className={styles.memberList}>
                {members.length === 0 ? (
                  <p className={styles.emptyText}>אין חברים בקבוצה.</p>
                ) : (
                  members.slice(0, MEMBERS_PREVIEW).map((m) => {
                  const isCurrentUser = m.user_id === user?.user_id;
                  const canRemove = isAdmin && !isCurrentUser && m.role !== 'admin';
                  const canPromote = isAdmin && m.role === 'member';
                  const showDropdown = canRemove || canPromote;
                  const isOpen = openDropdown === m.id;
                  return (
                    <li key={m.id} className={styles.memberRow}>
                      <div className={styles.memberInfo}>
                        <span className={styles.memberName}>{m.full_name ?? m.user_id}</span>
                        <span
                          className={`${styles.roleBadge} ${m.role === 'admin' ? styles.roleBadgeAdmin : ''}`}
                          title={m.role === 'admin' ? 'מנהל' : undefined}
                        >
                          {m.role === 'admin' ? (
                            <>
                              <Crown size={12} className={styles.roleCrown} />
                              מנהל
                            </>
                          ) : (
                            'חבר'
                          )}
                        </span>
                      </div>
                      {showDropdown && (
                        <div className={styles.memberDropdownWrap} ref={dropdownRef}>
                          <button
                            type="button"
                            className={styles.memberDropdownTrigger}
                            onClick={() => setOpenDropdown(isOpen ? null : m.id)}
                            aria-expanded={isOpen}
                            aria-haspopup="true"
                          >
                            <MoreVertical size={18} />
                          </button>
                          {isOpen && (
                            <div className={styles.memberDropdownMenu}>
                              {canPromote && (
                                <button
                                  type="button"
                                  className={styles.dropdownItem}
                                  onClick={() => handlePromoteMember(m.user_id)}
                                  disabled={actionLoading}
                                >
                                  קדם למנהל
                                </button>
                              )}
                              {canRemove && (
                                <button
                                  type="button"
                                  className={styles.dropdownItemDanger}
                                  onClick={() => handleRemoveMember(m.user_id)}
                                  disabled={actionLoading}
                                >
                                  הסר
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </li>
                  );
                  })
                )}
              </ul>
              {members.length > MEMBERS_PREVIEW && (
                <button
                  type="button"
                  className={styles.seeMoreBtn}
                  onClick={() => setMembersModalOpen(true)}
                >
                  See More · עוד ({members.length} חברים)
                </button>
              )}
              {membersModalOpen && (
                <div
                  className={styles.modalBackdrop}
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="members-modal-title"
                  onClick={() => setMembersModalOpen(false)}
                >
                  <div
                    className={styles.membersModalBox}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h2 id="members-modal-title" className={styles.membersModalTitle}>
                      חברי הקבוצה
                    </h2>
                    <input
                      type="text"
                      className={styles.membersSearchInput}
                      placeholder="חפש לפי שם..."
                      value={membersSearch}
                      onChange={(e) => setMembersSearch(e.target.value)}
                      aria-label="חיפוש חברים"
                    />
                    <ul className={styles.membersModalList}>
                      {filteredMembers.map((m) => (
                        <li key={m.id} className={styles.membersModalRow}>
                          <div
                            className={styles.memberAvatarSmall}
                            style={{
                              backgroundColor:
                                AVATAR_COLORS[Math.abs((m.full_name ?? '').length) % AVATAR_COLORS.length],
                            }}
                          >
                            {(m.full_name ?? 'נ').charAt(0).toUpperCase()}
                          </div>
                          <span className={styles.membersModalName}>
                            {m.full_name ?? m.user_id}
                          </span>
                          {m.role === 'admin' && (
                            <span className={styles.roleBadgeAdmin}>
                              <Crown size={12} /> מנהל
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                    {filteredMembers.length === 0 && (
                      <p className={styles.emptyText}>אין תוצאות</p>
                    )}
                    <button
                      type="button"
                      className={styles.btnOutline}
                      onClick={() => setMembersModalOpen(false)}
                    >
                      סגור
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
          <div className={styles.leaveSection}>
            <button
              type="button"
              className={styles.btnDanger}
              onClick={() => setConfirmLeave(true)}
              disabled={actionLoading}
            >
              צא מהקבוצה
            </button>
          </div>
        </>
      )}

      {activeTab === 'settings' && isAdmin && (
        <div className={styles.settingsSection}>
          <div>
            <h3 className={styles.settingsSectionTitle}>קוד הצטרפות</h3>
            <div className={styles.inviteRow}>
              <span className={styles.inviteUrl}>{inviteUrl}</span>
              <button
                type="button"
                className={styles.btnSecondary}
                onClick={handleCopyInvite}
              >
                העתק
              </button>
            </div>
            {copyInviteError && <p className={styles.inviteError}>{copyInviteError}</p>}
          </div>

          <hr className={styles.divider} />

          <div className={styles.dangerZone}>
            <h3 className={styles.dangerTitle}>אזור מסוכן</h3>
            <button
              type="button"
              className={styles.btnDanger}
              onClick={() => setConfirmClose(true)}
              disabled={actionLoading}
            >
              מחק קבוצה
            </button>
          </div>
        </div>
      )}

      <ConfirmModal
        open={confirmLeave}
        onClose={() => setConfirmLeave(false)}
        title="לעזוב את הקבוצה?"
        confirmLabel="עזוב"
        variant="danger"
        loading={actionLoading}
        onConfirm={handleLeave}
        titleId="confirm-leave-title"
      />
      <ConfirmModal
        open={confirmClose}
        onClose={() => setConfirmClose(false)}
        title="למחוק את הקבוצה?"
        description="כל החברים יוצאו והקבוצה לא תהיה זמינה. פעולה זו לא ניתנת לביטול."
        confirmLabel="מחק קבוצה"
        variant="danger"
        loading={actionLoading}
        onConfirm={handleClose}
        titleId="confirm-close-title"
      />
    </div>
  );
}
