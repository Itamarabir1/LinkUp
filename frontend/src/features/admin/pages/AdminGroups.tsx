import { useEffect, useState } from 'react';
import { fetchAdminGroups, type AdminGroupRow } from '../api/groups';
import page from '../styles/AdminPage.module.css';

type State =
  | { status: 'loading' }
  | { status: 'ready'; items: AdminGroupRow[] }
  | { status: 'error' };

export default function AdminGroups() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await fetchAdminGroups({ limit: 200 });
        if (!mounted) return;
        setState({ status: 'ready', items: Array.isArray(data) ? data : [] });
      } catch {
        if (!mounted) return;
        setState({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div>
      <h2 className={page.pageTitle}>קבוצות</h2>
      <p className={page.muted}>קריאה בלבד — רשימת קבוצות במערכת.</p>

      {state.status === 'loading' && <p className={page.muted}>טוען…</p>}
      {state.status === 'error' && <p className={page.error}>שגיאה בטעינה.</p>}
      {state.status === 'ready' && (
        <div className={page.tableWrap}>
          <table className={page.table}>
            <thead>
              <tr>
                <th>שם</th>
                <th>חברים</th>
                <th>מנהל</th>
                <th>אימייל מנהל</th>
                <th>פעיל</th>
                <th>נוצר</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((g) => (
                <tr key={g.group_id}>
                  <td>{g.name}</td>
                  <td>{g.member_count}</td>
                  <td>{g.admin_name || '—'}</td>
                  <td>{g.admin_email ?? '—'}</td>
                  <td>{g.is_active ? 'כן' : 'לא'}</td>
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
