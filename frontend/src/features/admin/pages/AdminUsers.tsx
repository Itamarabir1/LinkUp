import { useEffect, useMemo, useState } from 'react';
import { fetchAdminUsers, type AdminUserRow } from '../api/users';

type State =
  | { status: 'loading' }
  | { status: 'ready'; items: AdminUserRow[] }
  | { status: 'error' };

export default function AdminUsers() {
  const [q, setQ] = useState('');
  const [state, setState] = useState<State>({ status: 'loading' });

  const queryParams = useMemo(() => {
    const qq = q.trim();
    return qq ? { q: qq, limit: 50 } : { limit: 50 };
  }, [q]);

  useEffect(() => {
    let mounted = true;
    setState({ status: 'loading' });
    (async () => {
      try {
        const { data } = await fetchAdminUsers(queryParams);
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
  }, [queryParams]);

  return (
    <div>
      <h3>Users</h3>
      <div style={{ marginBottom: 12 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search email / phone / name"
          style={{ padding: 8, width: 320, maxWidth: '100%' }}
        />
      </div>

      {state.status === 'loading' && <p>Loading…</p>}
      {state.status === 'error' && <p>Failed to load users.</p>}
      {state.status === 'ready' && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
              <tr>
                {['name', 'email', 'phone', 'active', 'admin', 'verified', 'last_login'].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: 'left',
                      borderBottom: '1px solid #ddd',
                      padding: '8px 6px',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {state.items.map((u) => (
                <tr key={u.user_id}>
                  <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{u.full_name}</td>
                  <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{u.email ?? '—'}</td>
                  <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{u.phone_number}</td>
                  <td style={{ padding: '8px 6px' }}>{u.is_active ? 'yes' : 'no'}</td>
                  <td style={{ padding: '8px 6px' }}>{u.is_admin ? 'yes' : 'no'}</td>
                  <td style={{ padding: '8px 6px' }}>{u.is_verified ? 'yes' : 'no'}</td>
                  <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{u.last_login ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
