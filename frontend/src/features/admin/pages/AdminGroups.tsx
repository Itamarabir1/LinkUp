import { useAdminGroups } from '../queries/useAdminGroups';
import page from '../styles/AdminPage.module.css';

export default function AdminGroups() {
  const { data: items, isLoading, isError } = useAdminGroups({ limit: 200 });
  const status = isLoading ? 'loading' : isError ? 'error' : 'ready';

  return (
    <div>
      <h2 className={page.pageTitle}>קבוצות</h2>
      <p className={page.muted}>קריאה בלבד — רשימת קבוצות במערכת.</p>

      {status === 'loading' && <p className={page.muted}>טוען…</p>}
      {status === 'error' && <p className={page.error}>שגיאה בטעינה.</p>}
      {status === 'ready' && (
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
              {(items ?? []).map((g) => (
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
