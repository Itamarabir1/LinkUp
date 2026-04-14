import ErrorBanner from '../../components/ErrorBanner';
import { useTranslation } from 'react-i18next';
import type { GroupManageViewModel } from './useGroupManage';
import styles from './GroupManage.module.css';

export default function GroupSettingsTab({ vm }: { vm: GroupManageViewModel }) {
  const { t } = useTranslation('groups');
  return (
    <div className={styles.settingsSection}>
      <div>
        <h3 className={styles.settingsSectionTitle}>{t('inviteCodeTitle')}</h3>
        <div className={styles.inviteRow}>
          <span className={styles.inviteUrl}>{vm.inviteUrl}</span>
          <button type="button" className={styles.btnSecondary} onClick={() => void vm.handleCopyInvite()}>
            {t('copyLink')}
          </button>
        </div>
        {vm.copyInviteError ? (
          <ErrorBanner
            message={vm.copyInviteError}
            variant="compact"
            className={styles.inviteError}
          />
        ) : null}
      </div>

      <hr className={styles.divider} />

      <div className={styles.dangerZone}>
        <button
          type="button"
          className={styles.btnDanger}
          onClick={() => vm.setConfirmClose(true)}
          disabled={vm.actionLoading}
        >
          {t('deleteGroup')}
        </button>
      </div>
    </div>
  );
}
