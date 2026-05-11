import { useTranslation } from 'react-i18next';
import { useAdminQueues, useAdminSystemOverview, useAdminWorkers } from '../queries/useAdminOps';
import page from '../styles/AdminPage.module.css';

export default function AdminOps() {
  const { t } = useTranslation('admin');
  const system = useAdminSystemOverview();
  const queues = useAdminQueues();
  const workers = useAdminWorkers();

  const hasError = system.isError || queues.isError || workers.isError;
  const isLoading = system.isLoading || queues.isLoading || workers.isLoading;

  return (
    <div>
      <h2 className={page.pageTitle}>Admin Ops</h2>
      {isLoading && <p className={page.muted}>{t('loading_short')}</p>}
      {hasError && <p className={page.error}>{t('ops_error')}</p>}
      {!isLoading && !hasError && (
        <div className={page.grid2}>
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>System</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Outbox Pending</td>
                  <td>{system.data?.outbox.pending ?? 0}</td>
                </tr>
                <tr>
                  <td>Outbox Failed</td>
                  <td>{system.data?.outbox.failed ?? 0}</td>
                </tr>
                <tr>
                  <td>Billing Pending</td>
                  <td>{system.data?.billing.pending ?? 0}</td>
                </tr>
                <tr>
                  <td>Billing Failed</td>
                  <td>{system.data?.billing.failed ?? 0}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>Worker</th>
                  <th>Connected</th>
                </tr>
              </thead>
              <tbody>
                {(workers.data?.workers ?? []).map((w) => (
                  <tr key={w.name}>
                    <td>{w.name}</td>
                    <td>{w.rabbitmq_client_connected ? 'yes' : 'no'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>Queue</th>
                  <th>Retry</th>
                  <th>Delay</th>
                </tr>
              </thead>
              <tbody>
                {(queues.data?.queues ?? []).map((q) => (
                  <tr key={q.queue_name}>
                    <td>{q.queue_name}</td>
                    <td>{q.retry_enabled ? 'yes' : 'no'}</td>
                    <td>{q.retry_delay_ms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
