import ErrorBanner from '../../components/ErrorBanner';
import { useTranslation } from 'react-i18next';
import GroupManageContent from './GroupManageContent';
import GroupManageHeader from './GroupManageHeader';
import { useGroupManage } from './useGroupManage';
import styles from './GroupManage.module.css';

export default function GroupManage() {
  const { t } = useTranslation(['groups', 'common']);
  const vm = useGroupManage();

  if (!vm.groupId) {
    return (
      <div className={styles.page}>
        <ErrorBanner message={t('groups:groupNotFoundOrInvalid')} className={styles.pageError} />
      </div>
    );
  }

  if (!vm.isLoadingGroups && !vm.group) {
    return (
      <div className={styles.page}>
        <ErrorBanner message={t('groups:groupNotFoundOrInvalid')} className={styles.pageError} />
      </div>
    );
  }

  if (!vm.group) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>{t('common:loading')}</div>
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
