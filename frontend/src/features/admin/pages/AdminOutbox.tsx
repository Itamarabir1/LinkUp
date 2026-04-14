import { useEffect, useMemo, useState } from 'react';
import ConfirmModal from '../../../components/ConfirmModal/ConfirmModal';
import { triggerNotificationToast } from '../../../components/NotificationToast/notificationToast.utils';
import {
  fetchAdminOutbox,
  fetchAdminOutboxById,
  postAdminOutboxRequeue,
  type AdminOutboxDetail,
  type AdminOutboxRow,
} from '../api/outbox';
import { useAdminFetch } from '../hooks/useAdminFetch';
import page from '../styles/AdminPage.module.css';

type DetailState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; item: AdminOutboxDetail }
  | { status: 'error' };

export default function AdminOutbox() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailState>({ status: 'idle' });
  const [requeueId, setRequeueId] = useState<string | null>(null);
  const [requeueLoading, setRequeueLoading] = useState(false);

  const params = useMemo(() => ({ limit: 100, status: statusFilter || undefined }), [statusFilter]);
  const {
    status: listStatus,
    data: listData,
    reload: loadList,
  } = useAdminFetch<AdminOutboxRow[]>(() => fetchAdminOutbox(params));

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

  async function confirmRequeue() {
    if (!requeueId) return;
    setRequeueLoading(true);
    try {
      await postAdminOutboxRequeue(requeueId);
      triggerNotificationToast({ title: 'בוצע', body: 'האירוע הוחזר לתור.' });
      setRequeueId(null);
      if (selectedId === requeueId) setSelectedId(null);
      loadList();
    } catch {
      triggerNotificationToast({ title: 'שגיאה', body: 'לא ניתן להחזיר לתור.' });
    } finally {
      setRequeueLoading(false);
    }
  }

  const canRequeueDetail = detail.status === 'ready' && detail.item.status === 'FAILED';

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
            {detail.status === 'idle' && <p className={page.muted}>בחר שורה מהטבלה.</p>}
            {detail.status === 'loading' && <p className={page.muted}>טוען…</p>}
            {detail.status === 'error' && <p className={page.error}>שגיאה בטעינת פרטים.</p>}
            {detail.status === 'ready' && (
              <>
                {canRequeueDetail && (
                  <div className={page.toolbar}>
                    <button
                      type="button"
                      className={page.btnSmPrimary}
                      onClick={() => setRequeueId(detail.item.id)}
                    >
                      החזר לתור (requeue)
                    </button>
                  </div>
                )}
                <pre className={page.preJson}>{JSON.stringify(detail.item, null, 2)}</pre>
              </>
            )}
          </div>
        </div>
      )}

      <ConfirmModal
        open={requeueId !== null}
        onClose={() => !requeueLoading && setRequeueId(null)}
        title="החזרת אירוע לתור"
        description="לאשר החזרת אירוע שנכשל לסטטוס PENDING?"
        confirmLabel="אישור"
        variant="primary"
        loading={requeueLoading}
        onConfirm={confirmRequeue}
      />
    </div>
  );
}
