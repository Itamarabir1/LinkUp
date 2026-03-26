import { useEffect, useState } from 'react';
import { fetchAdminHealth, type AdminHealthResponse } from '../api/health';
import page from '../styles/AdminPage.module.css';

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

  if (state.status === 'loading') return <p className={page.muted}>טוען…</p>;
  if (state.status === 'error') return <p className={page.error}>שגיאה בטעינת בריאות.</p>;

  const { data } = state;
  return (
    <div>
      <h2 className={page.pageTitle}>בריאות מערכת</h2>
      <p className={page.muted}>
        סטטוס כללי: <strong>{data.status}</strong>
      </p>
      <div className={page.tableWrap}>
        <table className={page.table}>
          <tbody>
            <tr>
              <td>מסד נתונים</td>
              <td>{data.database}</td>
            </tr>
            <tr>
              <td>Redis</td>
              <td>{data.redis}</td>
            </tr>
            <tr>
              <td>RabbitMQ</td>
              <td>{data.rabbitmq}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
