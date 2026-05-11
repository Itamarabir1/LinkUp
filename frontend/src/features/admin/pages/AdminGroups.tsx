import { useTranslation } from 'react-i18next';
import { useAdminGroups } from '../queries/useAdminGroups';
import page from '../styles/AdminPage.module.css';

export default function AdminGroups() {
  const { t } = useTranslation('admin');
  const { data: items, isLoading, isError } = useAdminGroups({ limit: 200 });
  const status = isLoading ? 'loading' : isError ? 'error' : 'ready';

  return (
    <div>
      <h2 className={page.pageTitle}>{t('groups')}</h2>
      <p className={page.muted}>{t('groups_readonly')}</p>

      {status === 'loading' && <p className={page.muted}>{t('loading_short')}</p>}
      {status === 'error' && <p className={page.error}>{t('load_error')}</p>}
      {status === 'ready' && (
        <div className={page.tableWrap}>
          <table className={page.table}>
            <thead>
              <tr>
                <th>{t('name')}</th>
                <th>{t('members')}</th>
                <th>{t('group_admin')}</th>
                <th>{t('admin_email')}</th>
                <th>{t('is_active')}</th>
                <th>{t('created')}</th>
              </tr>
            </thead>
            <tbody>
              {(items ?? []).map((g) => (
                <tr key={g.group_id}>
                  <td>{g.name}</td>
                  <td>{g.member_count}</td>
                  <td>{g.admin_name || '—'}</td>
                  <td>{g.admin_email ?? '—'}</td>
                  <td>{g.is_active ? t('yes') : t('no')}</td>
                  <td>{g.created_at ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
