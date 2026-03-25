import { useEffect, useState } from 'react';
import { fetchAdminHealth, type AdminHealthResponse } from '../api/health';

type State =
  | { status: 'loading' }
  | { status: 'ready'; data: AdminHealthResponse }
  | { status: 'error' };

export default function AdminHealth() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await fetchAdminHealth();
        if (!mounted) return;
        setState({ status: 'ready', data });
      } catch {
        if (!mounted) return;
        setState({ status: 'error' });
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (state.status === 'loading') return <p>Loading health…</p>;
  if (state.status === 'error') return <p>Failed to load health.</p>;

  const { data } = state;
  return (
    <div>
      <h3>System health: {data.status}</h3>
      <ul>
        <li>database: {data.database}</li>
        <li>redis: {data.redis}</li>
        <li>rabbitmq: {data.rabbitmq}</li>
      </ul>
    </div>
  );
}
