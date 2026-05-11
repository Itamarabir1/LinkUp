import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAdminHealth } from '../queries/useAdminHealth';
import { useAdminSystemOverview } from '../queries/useAdminOps';
import page from '../styles/AdminPage.module.css';

function ServiceStatus({ ok, okLabel, errLabel }: { ok: boolean; okLabel: string; errLabel: string }) {
  return (
    <span className={page.healthRow}>
      <span className={`${page.healthDot} ${ok ? page.healthDotOk : page.healthDotErr}`} aria-hidden />
      {ok ? okLabel : errLabel}
    </span>
  );
}

export default function AdminHealth() {
  const { t } = useTranslation('admin');
  const health = useAdminHealth();
  const overview = useAdminSystemOverview();
  const { data, isLoading, isError } = health;
  if (isLoading) return <p className={page.muted}>{t('loading_short')}</p>;
  if (isError || !data) return <p className={page.error}>{t('health_load_error')}</p>;
  const healthy = data.status === 'healthy';
  const lastUpdated = health.dataUpdatedAt ? new Date(health.dataUpdatedAt).toLocaleString('he-IL') : '—';
  const outboxPending = overview.data?.outbox.pending ?? 0;
  const outboxFailed = overview.data?.outbox.failed ?? 0;
  const workerConnected = overview.data?.rabbitmq_clients.worker === true;

  return (
    <div>
      <div className={page.healthTitleRow}>
        <h2 className={page.healthPageTitle}>{t('system_health')}</h2>
        <span className={`${page.healthBadge} ${healthy ? page.healthBadgeOk : page.healthBadgeBad}`}>
          <span className={`${page.healthDot} ${healthy ? page.healthDotOk : page.healthDotErr}`} aria-hidden />
          {healthy ? t('health_all_ok') : t('health_has_issue')}
        </span>
        <button type="button" className={page.btnSm} onClick={() => void Promise.all([health.refetch(), overview.refetch()])}>
          {t('refresh')}
        </button>
        <Link to="/admin/ops" className={page.quickLink}>{t('go_to_ops')}</Link>
      </div>
      <p className={page.muted}>{t('last_updated', { time: lastUpdated })}</p>
      <div className={page.tableWrap}>
        <table className={page.table}>
          <tbody>
            <tr>
              <td>{t('database')}</td>
              <td>
                <ServiceStatus ok={data.database === 'ok'} okLabel={t('ok')} errLabel={t('error')} />
              </td>
            </tr>
            <tr>
              <td>Redis</td>
              <td>
                <ServiceStatus ok={data.redis === 'ok'} okLabel={t('ok')} errLabel={t('error')} />
              </td>
            </tr>
            <tr>
              <td>RabbitMQ</td>
              <td>
                <ServiceStatus ok={data.rabbitmq === 'ok'} okLabel={t('ok')} errLabel={t('error')} />
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
                <ServiceStatus ok={workerConnected} okLabel={t('ok')} errLabel={t('error')} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
