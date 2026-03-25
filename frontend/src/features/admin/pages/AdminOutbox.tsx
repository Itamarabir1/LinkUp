import { useEffect, useMemo, useState } from 'react';
import {
  fetchAdminOutbox,
  fetchAdminOutboxById,
  type AdminOutboxDetail,
  type AdminOutboxRow,
} from '../api/outbox';

type ListState =
  | { status: 'loading' }
  | { status: 'ready'; items: AdminOutboxRow[] }
  | { status: 'error' };

type DetailState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; item: AdminOutboxDetail }
  | { status: 'error' };

export default function AdminOutbox() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [list, setList] = useState<ListState>({ status: 'loading' });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailState>({ status: 'idle' });

  const params = useMemo(() => ({ limit: 100, status: statusFilter || undefined }), [statusFilter]);

  useEffect(() => {
    let mounted = true;
    setList({ status: 'loading' });
    (async () => {
      try {
        const { data } = await fetchAdminOutbox(params);
        if (!mounted) return;
        setList({ status: 'ready', items: Array.isArray(data) ? data : [] });
      } catch {
        if (!mounted) return;
        setList({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, [params]);

  useEffect(() => {
    let mounted = true;
    if (!selectedId) {
      setDetail({ status: 'idle' });
      return () => {
        mounted = false;
      };
    }
    setDetail({ status: 'loading' });
    (async () => {
      try {
        const { data } = await fetchAdminOutboxById(selectedId);
        if (!mounted) return;
        setDetail({ status: 'ready', item: data });
      } catch {
        if (!mounted) return;
        setDetail({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, [selectedId]);

  return (
    <div>
      <h3>Outbox</h3>
      <div style={{ marginBottom: 12, display: 'flex', gap: 12, alignItems: 'center' }}>
        <label>
          Status:{' '}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">(any)</option>
            <option value="PENDING">PENDING</option>
            <option value="PROCESSED">PROCESSED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </label>
        {selectedId && (
          <button onClick={() => setSelectedId(null)} type="button">
            Clear selection
          </button>
        )}
      </div>

      {list.status === 'loading' && <p>Loading…</p>}
      {list.status === 'error' && <p>Failed to load outbox.</p>}
      {list.status === 'ready' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr>
                  {['created_at', 'event_name', 'status', 'retries'].map((h) => (
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
                {list.items.map((e) => (
                  <tr
                    key={e.id}
                    onClick={() => setSelectedId(e.id)}
                    style={{
                      cursor: 'pointer',
                      background: selectedId === e.id ? '#f5f5f5' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{e.created_at}</td>
                    <td style={{ padding: '8px 6px', whiteSpace: 'nowrap' }}>{e.event_name}</td>
                    <td style={{ padding: '8px 6px' }}>{e.status}</td>
                    <td style={{ padding: '8px 6px' }}>{e.retry_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <h4 style={{ marginTop: 0 }}>Details</h4>
            {detail.status === 'idle' && <p>Select an event.</p>}
            {detail.status === 'loading' && <p>Loading details…</p>}
            {detail.status === 'error' && <p>Failed to load details.</p>}
            {detail.status === 'ready' && (
              <pre
                style={{
                  background: '#111',
                  color: '#eee',
                  padding: 12,
                  borderRadius: 6,
                  overflowX: 'auto',
                  maxHeight: 460,
                }}
              >
                {JSON.stringify(detail.item, null, 2)}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
