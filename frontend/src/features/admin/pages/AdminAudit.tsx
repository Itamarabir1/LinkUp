import { useMemo, useState } from 'react';
import { useAdminAudit } from '../queries/useAdminAudit';
import page from '../styles/AdminPage.module.css';

export default function AdminAudit() {
  const [action, setAction] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [offset, setOffset] = useState(0);
  const limit = 100;
  const params = useMemo(
    () => ({
      action: action || undefined,
      resource_type: resourceType || undefined,
      limit,
      offset,
    }),
    [action, resourceType, offset],
  );
  const { data, isLoading, isError } = useAdminAudit(params);
  const items = data?.items ?? [];

  return (
    <div>
      <h2 className={page.pageTitle}>Audit Log</h2>
      <div className={page.toolbar}>
        <input
          className={page.searchInput}
          placeholder="Filter by action"
          value={action}
          onChange={(e) => {
            setAction(e.target.value);
            setOffset(0);
          }}
        />
        <input
          className={page.searchInput}
          placeholder="Filter by resource_type"
          value={resourceType}
          onChange={(e) => {
            setResourceType(e.target.value);
            setOffset(0);
          }}
        />
      </div>

      {isLoading && <p className={page.muted}>טוען…</p>}
      {isError && <p className={page.error}>שגיאה בטעינה.</p>}
      {!isLoading && !isError && (
        <>
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Actor</th>
                  <th>Metadata</th>
                </tr>
              </thead>
              <tbody>
                {items.map((r) => (
                  <tr key={r.id}>
                    <td>{r.created_at ?? '—'}</td>
                    <td>{r.action}</td>
                    <td>{r.resource_type}</td>
                    <td>{r.actor_user_id ? `${r.actor_user_id.slice(0, 8)}…` : '—'}</td>
                    <td>
                      <code>{JSON.stringify(r.metadata ?? {})}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className={page.toolbar}>
            <button
              type="button"
              className={page.btnSm}
              disabled={offset === 0}
              onClick={() => setOffset((v) => Math.max(0, v - limit))}
            >
              הקודם
            </button>
            <button
              type="button"
              className={page.btnSm}
              disabled={data?.next_offset == null}
              onClick={() => setOffset(data?.next_offset ?? offset)}
            >
              הבא
            </button>
            <span className={page.muted}>
              {offset + 1}-{offset + items.length} מתוך {data?.total ?? 0}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
