import ConfirmModal from '../../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../../components/ErrorBanner';
import type { GroupManageViewModel } from './useGroupManage';
import GroupMembersTab from './GroupMembersTab';
import GroupRidesTab from './GroupRidesTab';
import GroupSettingsTab from './GroupSettingsTab';
import styles from './GroupManage.module.css';

export interface GroupManageContentProps {
  vm: GroupManageViewModel;
}

export default function GroupManageContent({ vm }: GroupManageContentProps) {
  const { isAdmin } = vm;

  return (
    <>
      <div role="tablist" className={styles.tabs}>
        <button
          type="button"
          role="tab"
          aria-selected={vm.activeTab === 'rides'}
          className={vm.activeTab === 'rides' ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => vm.setActiveTab('rides')}
        >
          נסיעות
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vm.activeTab === 'members'}
          className={vm.activeTab === 'members' ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => vm.setActiveTab('members')}
        >
          חברים
        </button>
        {isAdmin && (
          <button
            type="button"
            role="tab"
            aria-selected={vm.activeTab === 'settings'}
            className={vm.activeTab === 'settings' ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => vm.setActiveTab('settings')}
          >
            הגדרות
          </button>
        )}
      </div>

      {vm.error ? <ErrorBanner message={vm.error} className={styles.pageError} /> : null}

      <div className={styles.contentArea}>
        {vm.activeTab === 'rides' && <GroupRidesTab vm={vm} />}
        {vm.activeTab === 'members' && <GroupMembersTab vm={vm} />}
        {vm.activeTab === 'settings' && isAdmin && <GroupSettingsTab vm={vm} />}
      </div>

      <ConfirmModal
        open={vm.confirmLeave}
        onClose={() => vm.setConfirmLeave(false)}
        title="לעזוב את הקבוצה?"
        confirmLabel="עזוב"
        variant="danger"
        loading={vm.actionLoading}
        onConfirm={vm.handleLeave}
        titleId="confirm-leave-title"
      />
      <ConfirmModal
        open={vm.confirmClose}
        onClose={() => vm.setConfirmClose(false)}
        title="למחוק את הקבוצה?"
        description="כל החברים יוצאו והקבוצה לא תהיה זמינה. פעולה זו לא ניתנת לביטול."
        confirmLabel="מחק קבוצה"
        variant="danger"
        loading={vm.actionLoading}
        onConfirm={vm.handleClose}
        titleId="confirm-close-title"
      />
    </>
  );
}
