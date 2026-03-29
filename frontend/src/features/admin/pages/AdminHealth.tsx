import { useEffect, useState } from 'react';
import { fetchAdminHealth, type AdminHealthResponse } from '../api/health';
import page from '../styles/AdminPage.module.css';

type State =
  | { status: 'loading' }
  | { status: 'ready'; data: AdminHealthResponse }
  | { status: 'error' };

function ServiceStatus({ ok }: { ok: boolean }) {
  return (
    <span className={page.healthRow}>
      <span className={`${page.healthDot} ${ok ? page.healthDotOk : page.healthDotErr}`} aria-hidden />
      {ok ? 'תקין' : 'שגיאה'}
    </span>
  );
}

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
  const healthy = data.status === 'healthy';

  return (
    <div>
      <div className={page.healthTitleRow}>
        <h2 className={page.healthPageTitle}>בריאות מערכת</h2>
        <span className={`${page.healthBadge} ${healthy ? page.healthBadgeOk : page.healthBadgeBad}`}>
          <span className={`${page.healthDot} ${healthy ? page.healthDotOk : page.healthDotErr}`} aria-hidden />
          {healthy ? 'הכל תקין' : 'יש תקלה'}
        </span>
      </div>
      <div className={page.tableWrap}>
        <table className={page.table}>
          <tbody>
            <tr>
              <td>מסד נתונים</td>
              <td>
                <ServiceStatus ok={data.database === 'ok'} />
              </td>
            </tr>
            <tr>
              <td>Redis</td>
              <td>
                <ServiceStatus ok={data.redis === 'ok'} />
              </td>
            </tr>
            <tr>
              <td>RabbitMQ</td>
              <td>
                <ServiceStatus ok={data.rabbitmq === 'ok'} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
