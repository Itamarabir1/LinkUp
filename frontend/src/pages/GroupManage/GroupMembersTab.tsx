import { useEffect } from 'react';
import { Crown, MoreVertical } from 'lucide-react';
import type { GroupManageViewModel } from './useGroupManage';
import styles from './GroupManage.module.css';

export default function GroupMembersTab({ vm }: { vm: GroupManageViewModel }) {
  const { user, isAdmin, openDropdown, setOpenDropdown } = vm;

  useEffect(() => {
    if (!openDropdown) return;
    const selector = `[data-member-dropdown="${CSS.escape(openDropdown)}"]`;
    const onMouseDown = (e: MouseEvent) => {
      const root = document.querySelector(selector);
      if (root && !root.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [openDropdown, setOpenDropdown]);

  return (
    <>
      {vm.loadingMembers ? (
        <div className={styles.pageLoading}>טוען חברים...</div>
      ) : (
        <>
          <p className={styles.membersCountHeader}>{vm.members.length} חברים</p>
          <ul className={styles.memberList}>
            {vm.members.length === 0 ? (
              <p className={styles.emptyText}>אין חברים בקבוצה.</p>
            ) : (
              vm.members.slice(0, vm.membersPreview).map((m) => {
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
                      <div className={styles.memberDropdownWrap} data-member-dropdown={m.id}>
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
                                onClick={() => void vm.handlePromoteMember(m.user_id)}
                                disabled={vm.actionLoading}
                              >
                                קדם למנהל
                              </button>
                            )}
                            {canRemove && (
                              <button
                                type="button"
                                className={styles.dropdownItemDanger}
                                onClick={() => void vm.handleRemoveMember(m.user_id)}
                                disabled={vm.actionLoading}
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
          {vm.members.length > vm.membersPreview && (
            <button type="button" className={styles.seeMoreBtn} onClick={() => vm.setMembersModalOpen(true)}>
              הצג את כל החברים · {vm.members.length}
            </button>
          )}
          {vm.membersModalOpen && (
            <div
              className={styles.modalBackdrop}
              role="dialog"
              aria-modal="true"
              aria-labelledby="members-modal-title"
              onClick={() => vm.setMembersModalOpen(false)}
            >
              <div className={styles.membersModalBox} onClick={(e) => e.stopPropagation()}>
                <h2 id="members-modal-title" className={styles.membersModalTitle}>
                  חברי הקבוצה
                </h2>
                <input
                  type="text"
                  className={styles.membersSearchInput}
                  placeholder="חפש לפי שם..."
                  value={vm.membersSearch}
                  onChange={(e) => vm.setMembersSearch(e.target.value)}
                  aria-label="חיפוש חברים"
                />
                <ul className={styles.membersModalList}>
                  {vm.filteredMembers.map((m) => (
                    <li key={m.id} className={styles.membersModalRow}>
                      <div
                        className={styles.memberAvatarSmall}
                        style={{
                          ['--avatar-bg' as string]:
                            vm.avatarColors[Math.abs((m.full_name ?? '').length) % vm.avatarColors.length],
                        }}
                      >
                        {(m.full_name ?? 'נ').charAt(0).toUpperCase()}
                      </div>
                      <span className={styles.membersModalName}>{m.full_name ?? m.user_id}</span>
                      {m.role === 'admin' && (
                        <span className={styles.roleBadgeAdmin}>
                          <Crown size={12} /> מנהל
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
                {vm.filteredMembers.length === 0 && <p className={styles.emptyText}>אין תוצאות</p>}
                <button type="button" className={styles.btnOutline} onClick={() => vm.setMembersModalOpen(false)}>
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
          onClick={() => vm.setConfirmLeave(true)}
          disabled={vm.actionLoading}
        >
          צא מהקבוצה
        </button>
      </div>
    </>
  );
}
