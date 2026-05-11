import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import {
  useAdminOutbox,
  useAdminOutboxDetail,
} from '../queries/useAdminOutbox';
import { useRequeueOutbox } from '../mutations/useAdminOutboxMutations';
import page from '../styles/AdminPage.module.css';

export default function AdminOutbox() {
  const { t } = useTranslation('admin');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [requeueId, setRequeueId] = useState<string | null>(null);
  const requeue = useRequeueOutbox();

  const params = useMemo(() => ({ limit: 100, status: statusFilter || undefined }), [statusFilter]);
  const { data: listData, isLoading, isError } = useAdminOutbox(params);
  const {
    data: detailItem,
    isLoading: detailLoading,
    isError: detailError,
  } = useAdminOutboxDetail(selectedId);
  const listStatus: 'loading' | 'error' | 'ready' = isLoading ? 'loading' : isError ? 'error' : 'ready';

  async function confirmRequeue() {
    if (!requeueId) return;
    try {
      await requeue.mutateAsync(requeueId);
      setRequeueId(null);
      if (selectedId === requeueId) setSelectedId(null);
    } catch {
      // toast handled in mutation hook
    }
  }

  const canRequeueDetail = detailItem?.status === 'FAILED';

  return (
    <div>
      <h2 className={page.pageTitle}>Outbox</h2>
      <div className={page.toolbar}>
        <label className={page.muted}>
          {t('status_label')}{' '}
          <select
            className={page.select}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">{t('all')}</option>
            <option value="PENDING">PENDING</option>
            <option value="PROCESSED">PROCESSED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </label>
        {selectedId && (
          <button type="button" className={page.btnSm} onClick={() => setSelectedId(null)}>
            {t('clear_selection')}
          </button>
        )}
      </div>

      {listStatus === 'loading' && <p className={page.muted}>{t('loading_short')}</p>}
      {listStatus === 'error' && <p className={page.error}>{t('load_error')}</p>}
      {listStatus === 'ready' && (
        <div className={page.grid2}>
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>{t('created')}</th>
                  <th>{t('event')}</th>
                  <th>{t('status')}</th>
                  <th>{t('attempts')}</th>
                </tr>
              </thead>
              <tbody>
                {(listData ?? []).map((e) => (
                  <tr
                    key={e.id}
                    className={`${page.rowClick} ${selectedId === e.id ? page.rowSelected : ''}`}
                    onClick={() => setSelectedId(e.id)}
                  >
                    <td>{e.created_at}</td>
                    <td>{e.event_name}</td>
                    <td>
                      {(() => {
                        const badgeClass = {
                          PENDING: page.badgeWarn,
                          PROCESSED: page.badgeOk,
                          FAILED: page.badgeErr,
                        }[e.status] ?? page.badgeGray;
                        return <span className={`${page.badge} ${badgeClass}`}>{e.status}</span>;
                      })()}
                    </td>
                    <td>{e.retry_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <h3 className={page.subheading}>{t('outbox_detail')}</h3>
            {!selectedId && <p className={page.muted}>{t('outbox_select_row')}</p>}
            {selectedId && detailLoading && <p className={page.muted}>{t('loading_short')}</p>}
            {selectedId && detailError && <p className={page.error}>{t('outbox_detail_error')}</p>}
            {!!detailItem && (
              <>
                {canRequeueDetail && (
                  <div className={page.toolbar}>
                    <button
                      type="button"
                      className={page.btnSmPrimary}
                      onClick={() => setRequeueId(detailItem.id)}
                    >
                      {t('outbox_requeue')}
                    </button>
                  </div>
                )}
                <pre className={page.preJson}>{JSON.stringify(detailItem, null, 2)}</pre>
              </>
            )}
          </div>
        </div>
      )}

      <ConfirmModal
        open={requeueId !== null}
        onClose={() => !requeue.isPending && setRequeueId(null)}
        title={t('outbox_requeue_title')}
        description={t('outbox_requeue_confirm')}
        confirmLabel={t('confirm_label')}
        variant="primary"
        loading={requeue.isPending}
        onConfirm={confirmRequeue}
      />
    </div>
  );
}
