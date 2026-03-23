import ErrorBanner from '../../components/ErrorBanner';
import type { GroupManageViewModel } from './useGroupManage';
import styles from './GroupManage.module.css';

export default function GroupSettingsTab({ vm }: { vm: GroupManageViewModel }) {
  return (
    <div className={styles.settingsSection}>
      <div>
        <h3 className={styles.settingsSectionTitle}>קוד הצטרפות</h3>
        <div className={styles.inviteRow}>
          <span className={styles.inviteUrl}>{vm.inviteUrl}</span>
          <button type="button" className={styles.btnSecondary} onClick={() => void vm.handleCopyInvite()}>
            העתק
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
        <h3 className={styles.dangerTitle}>אזור מסוכן</h3>
        <button
          type="button"
          className={styles.btnDanger}
          onClick={() => vm.setConfirmClose(true)}
          disabled={vm.actionLoading}
        >
          מחק קבוצה
        </button>
      </div>
    </div>
  );
}
