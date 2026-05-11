import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import type { AdminUserRow } from '../api/users';
import { useAdminUsers } from '../queries/useAdminUsers';
import { useToggleUserActive, useToggleUserAdmin } from '../mutations/useAdminUserMutations';
import page from '../styles/AdminPage.module.css';

type PendingModal =
  | { kind: 'active'; user: AdminUserRow }
  | { kind: 'admin'; user: AdminUserRow }
  | null;

function stringToColor(str: string): string {
  const colors = ['#4f6ef7', '#06b6d4', '#22c55e', '#f59e0b', '#a855f7', '#ef4444'];
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

export default function AdminUsers() {
  const { t } = useTranslation('admin');
  const [q, setQ] = useState('');
  const [modal, setModal] = useState<PendingModal>(null);

  const queryParams = useMemo(() => {
    const qq = q.trim();
    return qq ? { q: qq, limit: 50 } : { limit: 50 };
  }, [q]);
  const { data, isLoading, isError } = useAdminUsers(queryParams);
  const items = useMemo(() => data ?? [], [data]);
  const toggleActive = useToggleUserActive();
  const toggleAdmin = useToggleUserAdmin();
  const mutating = toggleActive.isPending || toggleAdmin.isPending;
  const mutatingId = modal?.user.user_id ?? null;
  const status: 'loading' | 'error' | 'ready' = isLoading ? 'loading' : isError ? 'error' : 'ready';

  const listSummary = useMemo(() => {
    if (status !== 'ready') return null;
    const shown = items.length;
    const activeCount = items.filter((u) => u.is_active).length;
    const adminCount = items.filter((u) => u.is_admin).length;
    return { shown, activeCount, adminCount };
  }, [items, status]);

  async function runMutation() {
    if (!modal) return;
    const uid = modal.user.user_id;
    try {
      if (modal.kind === 'active') {
        await toggleActive.mutateAsync(uid);
      } else {
        await toggleAdmin.mutateAsync({ userId: uid, makeAdmin: !modal.user.is_admin });
      }
      setModal(null);
    } catch {
      // toast handled in mutation hook
    }
  }

  return (
    <div>
      <h2 className={page.pageTitle}>{t('users')}</h2>
      <div className={page.toolbar}>
        <input
          className={page.searchInput}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('search_placeholder')}
          type="search"
        />
      </div>

      {status === 'loading' && <p className={page.muted}>{t('loading_short')}</p>}
      {status === 'error' && <p className={page.error}>{t('load_error')}</p>}
      {status === 'ready' && listSummary && (
        <p className={`${page.muted} ${page.usersSummary}`}>
          {t('users_summary', {
            shown: listSummary.shown,
            active: listSummary.activeCount,
            admins: listSummary.adminCount,
          })}
        </p>
      )}
      {status === 'ready' && (
        <div className={page.tableWrap}>
          <table className={page.table}>
            <thead>
              <tr>
                <th>{t('name')}</th>
                <th>{t('email')}</th>
                <th>{t('phone')}</th>
                <th>{t('is_active')}</th>
                <th>{t('is_admin')}</th>
                <th>{t('is_verified')}</th>
                <th>{t('last_login')}</th>
                <th>{t('actions')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((u) => (
                <tr key={u.user_id}>
                  <td>
                    <div className={page.userCell}>
                      <div
                        className={page.avatar}
                        style={{ background: stringToColor(u.user_id) }}
                      >
                        {(u.full_name || '?').charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className={page.userName}>{u.full_name}</div>
                        <div className={page.userEmail}>{u.email ?? '—'}</div>
                      </div>
                    </div>
                  </td>
                  <td>{u.email ?? '—'}</td>
                  <td>{u.phone_number}</td>
                  <td>
                    {u.is_active ? <span className={`${page.badge} ${page.badgeOk}`}>{t('yes')}</span>
                      : <span className={`${page.badge} ${page.badgeErr}`}>{t('no')}</span>}
                  </td>
                  <td>
                    {u.is_admin ? <span className={`${page.badge} ${page.badgeInfo}`}>{t('yes')}</span>
                      : <span className={`${page.badge} ${page.badgeGray}`}>{t('no')}</span>}
                  </td>
                  <td>
                    {u.is_verified ? <span className={`${page.badge} ${page.badgeOk}`}>{t('yes')}</span>
                      : <span className={`${page.badge} ${page.badgeGray}`}>{t('no')}</span>}
                  </td>
                  <td>{u.last_login ?? '—'}</td>
                  <td className={page.actionsCell}>
                    <button
                      type="button"
                      className={page.btnSm}
                      disabled={mutating && mutatingId === u.user_id}
                      onClick={() => setModal({ kind: 'active', user: u })}
                    >
                      {u.is_active ? t('deactivate') : t('activate')}
                    </button>
                    <button
                      type="button"
                      className={page.btnSm}
                      disabled={mutating && mutatingId === u.user_id}
                      onClick={() => setModal({ kind: 'admin', user: u })}
                    >
                      {u.is_admin ? t('remove_admin') : t('make_admin')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmModal
        open={modal !== null}
        onClose={() => !mutating && setModal(null)}
        title={modal?.kind === 'active' ? t('toggle_active_title') : t('toggle_admin_title')}
        description={
          modal
            ? t('confirm_user_change', {
                name: modal.user.full_name,
                identifier: modal.user.email ?? modal.user.phone_number,
              })
            : undefined
        }
        confirmLabel={t('confirm_label')}
        cancelLabel={t('cancel_label')}
        variant="primary"
        loading={mutating}
        onConfirm={runMutation}
      />
    </div>
  );
}
