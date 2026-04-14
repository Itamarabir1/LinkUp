import ConfirmModal from '../../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../../components/ErrorBanner';
import { useTranslation } from 'react-i18next';
import type { GroupManageViewModel } from './useGroupManage';
import GroupMembersTab from './GroupMembersTab';
import GroupRidesTab from './GroupRidesTab';
import GroupSettingsTab from './GroupSettingsTab';
import styles from './GroupManage.module.css';

export interface GroupManageContentProps {
  vm: GroupManageViewModel;
}

export default function GroupManageContent({ vm }: GroupManageContentProps) {
  const { t } = useTranslation(['groups', 'common']);
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
          {t('groups:ridesTab')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={vm.activeTab === 'members'}
          className={vm.activeTab === 'members' ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => vm.setActiveTab('members')}
        >
          {t('groups:membersTab')}
        </button>
        {isAdmin && (
          <button
            type="button"
            role="tab"
            aria-selected={vm.activeTab === 'settings'}
            className={vm.activeTab === 'settings' ? `${styles.tab} ${styles.tabActive}` : styles.tab}
            onClick={() => vm.setActiveTab('settings')}
          >
            {t('groups:settingsTab')}
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
        title={t('groups:leaveGroup')}
        confirmLabel={t('groups:leaveGroup')}
        variant="danger"
        loading={vm.actionLoading}
        onConfirm={vm.handleLeave}
        titleId="confirm-leave-title"
      />
      <ConfirmModal
        open={vm.confirmClose}
        onClose={() => vm.setConfirmClose(false)}
        title={t('groups:deleteGroup')}
        description={t('groups:deleteGroupWarning')}
        confirmLabel={t('groups:deleteGroup')}
        variant="danger"
        loading={vm.actionLoading}
        onConfirm={vm.handleClose}
        titleId="confirm-close-title"
      />
    </>
  );
}
