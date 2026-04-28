import { Link } from 'react-router-dom';
import { useAdminHealth } from '../queries/useAdminHealth';
import { useAdminSystemOverview } from '../queries/useAdminOps';
import page from '../styles/AdminPage.module.css';

function ServiceStatus({ ok }: { ok: boolean }) {
  return (
    <span className={page.healthRow}>
      <span className={`${page.healthDot} ${ok ? page.healthDotOk : page.healthDotErr}`} aria-hidden />
      {ok ? 'תקין' : 'שגיאה'}
    </span>
  );
}

export default function AdminHealth() {
  const health = useAdminHealth();
  const overview = useAdminSystemOverview();
  const { data, isLoading, isError } = health;
  if (isLoading) return <p className={page.muted}>טוען…</p>;
  if (isError || !data) return <p className={page.error}>שגיאה בטעינת בריאות.</p>;
  const healthy = data.status === 'healthy';
  const lastUpdated = health.dataUpdatedAt ? new Date(health.dataUpdatedAt).toLocaleString('he-IL') : '—';
  const outboxPending = overview.data?.outbox.pending ?? 0;
  const outboxFailed = overview.data?.outbox.failed ?? 0;
  const workerConnected = overview.data?.rabbitmq_clients.worker === true;

  return (
    <div>
      <div className={page.healthTitleRow}>
        <h2 className={page.healthPageTitle}>בריאות מערכת</h2>
        <span className={`${page.healthBadge} ${healthy ? page.healthBadgeOk : page.healthBadgeBad}`}>
          <span className={`${page.healthDot} ${healthy ? page.healthDotOk : page.healthDotErr}`} aria-hidden />
          {healthy ? 'הכל תקין' : 'יש תקלה'}
        </span>
        <button type="button" className={page.btnSm} onClick={() => void Promise.all([health.refetch(), overview.refetch()])}>
          רענון
        </button>
        <Link to="/admin/ops" className={page.quickLink}>מעבר ל-Ops</Link>
      </div>
      <p className={page.muted}>עודכן לאחרונה: {lastUpdated}</p>
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
            <tr>
              <td>Outbox (Pending / Failed)</td>
              <td>
                {outboxPending} / {outboxFailed}
              </td>
            </tr>
            <tr>
              <td>Worker Connection</td>
              <td>
                <ServiceStatus ok={workerConnected} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
