import ErrorBanner from '../../components/ErrorBanner';
import GroupManageContent from './GroupManageContent';
import GroupManageHeader from './GroupManageHeader';
import { useGroupManage } from './useGroupManage';
import styles from './GroupManage.module.css';

export default function GroupManage() {
  const vm = useGroupManage();

  if (!vm.groupId) {
    return (
      <div className={styles.page}>
        <ErrorBanner message="חסר מזהה קבוצה." className={styles.pageError} />
      </div>
    );
  }

  if (!vm.isLoadingGroups && !vm.group) {
    return (
      <div className={styles.page}>
        <ErrorBanner message="הקבוצה לא נמצאה או שאין לך גישה אליה." className={styles.pageError} />
      </div>
    );
  }

  if (!vm.group) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>טוען...</div>
      </div>
    );
  }

  const { group } = vm;

  return (
    <div className={styles.page}>
      <GroupManageHeader vm={vm} group={group} />
      <GroupManageContent vm={vm} />
    </div>
  );
}
