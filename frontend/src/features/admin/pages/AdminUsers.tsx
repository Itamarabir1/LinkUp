import { useCallback, useEffect, useMemo, useState } from 'react';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';
import {
  fetchAdminUsers,
  patchAdminUserActive,
  patchAdminUserAdmin,
  type AdminUserRow,
} from '../api/users';
import page from '../styles/AdminPage.module.css';

type State =
  | { status: 'loading' }
  | { status: 'ready'; items: AdminUserRow[] }
  | { status: 'error' };

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
  const [q, setQ] = useState('');
  const [state, setState] = useState<State>({ status: 'loading' });
  const [modal, setModal] = useState<PendingModal>(null);
  const [mutatingId, setMutatingId] = useState<string | null>(null);

  const queryParams = useMemo(() => {
    const qq = q.trim();
    return qq ? { q: qq, limit: 50 } : { limit: 50 };
  }, [q]);

  const load = useCallback(async () => {
    setState({ status: 'loading' });
    try {
      const { data } = await fetchAdminUsers(queryParams);
      setState({ status: 'ready', items: Array.isArray(data) ? data : [] });
    } catch {
      setState({ status: 'error' });
    }
  }, [queryParams]);

  useEffect(() => {
    void load();
  }, [load]);

  const listSummary = useMemo(() => {
    if (state.status !== 'ready') return null;
    const items = state.items;
    const shown = items.length;
    const activeCount = items.filter((u) => u.is_active).length;
    const adminCount = items.filter((u) => u.is_admin).length;
    return { shown, activeCount, adminCount };
  }, [state]);

  async function runMutation() {
    if (!modal) return;
    const uid = modal.user.user_id;
    setMutatingId(uid);
    try {
      if (modal.kind === 'active') {
        await patchAdminUserActive(uid);
        triggerNotificationToast({
          title: 'עודכן',
          body: 'סטטוס פעילות המשתמש עודכן.',
        });
      } else {
        await patchAdminUserAdmin(uid);
        triggerNotificationToast({
          title: 'עודכן',
          body: 'סטטוס אדמין עודכן.',
        });
      }
      setModal(null);
      await load();
    } catch {
      triggerNotificationToast({
        title: 'שגיאה',
        body: 'הפעולה נכשלה.',
      });
    } finally {
      setMutatingId(null);
    }
  }

  return (
    <div>
      <h2 className={page.pageTitle}>משתמשים</h2>
      <div className={page.toolbar}>
        <input
          className={page.searchInput}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="חיפוש אימייל / טלפון / שם"
          type="search"
        />
      </div>

      {state.status === 'loading' && <p className={page.muted}>טוען…</p>}
      {state.status === 'error' && <p className={page.error}>שגיאה בטעינה.</p>}
      {state.status === 'ready' && listSummary && (
        <p className={`${page.muted} ${page.usersSummary}`}>
          בתוצאות המוצגות: {listSummary.shown} משתמשים | {listSummary.activeCount} פעילים |{' '}
          {listSummary.adminCount} אדמינים
        </p>
      )}
      {state.status === 'ready' && (
        <div className={page.tableWrap}>
          <table className={page.table}>
            <thead>
              <tr>
                <th>שם</th>
                <th>אימייל</th>
                <th>טלפון</th>
                <th>פעיל</th>
                <th>אדמין</th>
                <th>מאומת</th>
                <th>התחברות אחרונה</th>
                <th>פעולות</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((u) => (
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
                    {u.is_active ? <span className={`${page.badge} ${page.badgeOk}`}>כן</span>
                      : <span className={`${page.badge} ${page.badgeErr}`}>לא</span>}
                  </td>
                  <td>
                    {u.is_admin ? <span className={`${page.badge} ${page.badgeInfo}`}>כן</span>
                      : <span className={`${page.badge} ${page.badgeGray}`}>לא</span>}
                  </td>
                  <td>
                    {u.is_verified ? <span className={`${page.badge} ${page.badgeOk}`}>כן</span>
                      : <span className={`${page.badge} ${page.badgeGray}`}>לא</span>}
                  </td>
                  <td>{u.last_login ?? '—'}</td>
                  <td className={page.actionsCell}>
                    <button
                      type="button"
                      className={page.btnSm}
                      disabled={mutatingId === u.user_id}
                      onClick={() => setModal({ kind: 'active', user: u })}
                    >
                      {u.is_active ? 'השבת' : 'הפעל'}
                    </button>
                    <button
                      type="button"
                      className={page.btnSm}
                      disabled={mutatingId === u.user_id}
                      onClick={() => setModal({ kind: 'admin', user: u })}
                    >
                      {u.is_admin ? 'הסר אדמין' : 'הפוך לאדמין'}
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
        onClose={() => !mutatingId && setModal(null)}
        title={modal?.kind === 'active' ? 'שינוי פעילות משתמש' : 'שינוי הרשאת אדמין'}
        description={
          modal
            ? `האם לבצע את השינוי עבור ${modal.user.full_name} (${modal.user.email ?? modal.user.phone_number})?`
            : undefined
        }
        confirmLabel="אישור"
        cancelLabel="ביטול"
        variant="primary"
        loading={mutatingId !== null}
        onConfirm={runMutation}
      />
    </div>
  );
}
