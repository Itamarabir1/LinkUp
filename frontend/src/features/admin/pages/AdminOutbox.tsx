import { useMemo, useState } from 'react';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import {
  useAdminOutbox,
  useAdminOutboxDetail,
} from '../queries/useAdminOutbox';
import { useRequeueOutbox } from '../mutations/useAdminOutboxMutations';
import page from '../styles/AdminPage.module.css';

export default function AdminOutbox() {
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
          סטטוס:{' '}
          <select
            className={page.select}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">הכל</option>
            <option value="PENDING">PENDING</option>
            <option value="PROCESSED">PROCESSED</option>
            <option value="FAILED">FAILED</option>
          </select>
        </label>
        {selectedId && (
          <button type="button" className={page.btnSm} onClick={() => setSelectedId(null)}>
            נקה בחירה
          </button>
        )}
      </div>

      {listStatus === 'loading' && <p className={page.muted}>טוען…</p>}
      {listStatus === 'error' && <p className={page.error}>שגיאה בטעינה.</p>}
      {listStatus === 'ready' && (
        <div className={page.grid2}>
          <div className={page.tableWrap}>
            <table className={page.table}>
              <thead>
                <tr>
                  <th>נוצר</th>
                  <th>אירוע</th>
                  <th>סטטוס</th>
                  <th>ניסיונות</th>
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
            <h3 className={page.subheading}>פרטים</h3>
            {!selectedId && <p className={page.muted}>בחר שורה מהטבלה.</p>}
            {selectedId && detailLoading && <p className={page.muted}>טוען…</p>}
            {selectedId && detailError && <p className={page.error}>שגיאה בטעינת פרטים.</p>}
            {!!detailItem && (
              <>
                {canRequeueDetail && (
                  <div className={page.toolbar}>
                    <button
                      type="button"
                      className={page.btnSmPrimary}
                      onClick={() => setRequeueId(detailItem.id)}
                    >
                      החזר לתור (requeue)
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
        title="החזרת אירוע לתור"
        description="לאשר החזרת אירוע שנכשל לסטטוס PENDING?"
        confirmLabel="אישור"
        variant="primary"
        loading={requeue.isPending}
        onConfirm={confirmRequeue}
      />
    </div>
  );
}
