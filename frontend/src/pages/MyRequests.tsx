import { useNavigate } from 'react-router-dom';
import { Search, X } from 'lucide-react';
import { useGroup } from '../context/GroupContext';
import { useMyRequests } from './useMyRequests';
import type { ChipItem } from '../components/Chips/Chips';
import Chips from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../components/ErrorBanner';
import { formatDateTimeNoSeconds } from '../utils/date';
import { getRideSourceLabel } from '../utils/rideDisplay';
import HistorySection from '../components/HistorySection/HistorySection';
import styles from './MyRequests.module.css';

const statusLabels: Record<string, string> = {
  active: 'מחפש',
  pending: 'ממתין לאישור',
  approved: 'אושר',
  rejected: 'נדחה',
  completed: 'הושלם',
  expired: 'פג תוקף',
  matched: 'נמצאה נסיעה',
  cancelled: 'בוטל',
};

export default function MyRequests() {
  const navigate = useNavigate();
  const { myGroups, activeChipId, setActiveChipId } = useGroup();

  const {
    requests,
    loading,
    error,
    requestToCancel,
    setRequestToCancel,
    cancelling,
    confirmCancelRequest,
  } = useMyRequests();

  const chipItems: ChipItem[] = [
    { id: 'all', label: 'הכל' },
    { id: 'public', label: 'ציבורי' },
    ...myGroups.map((g) => ({ id: g.group_id, label: g.name })),
  ];

  const displayedRequests = requests.filter((r) => {
    if (activeChipId === 'all') return true;
    if (activeChipId === 'public') return !r.group_id;
    return r.group_id === activeChipId;
  });
  const activeRequests = displayedRequests.filter((r) => r.status !== 'cancelled' && r.status !== 'completed' && r.status !== 'expired');
  const pastRequests = displayedRequests.filter((r) => r.status === 'cancelled' || r.status === 'completed' || r.status === 'expired');

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>טוען...</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Chips items={chipItems} activeId={activeChipId} onChange={setActiveChipId} />
      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}
      {displayedRequests.length === 0 ? (
        <div className={styles.emptyState}>
          <Search size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>אין בקשות טרמפ פעילות</h2>
          <p className={styles.emptySubtitle}>חפש טרמפ כדי להתחיל</p>
          <button
            type="button"
            className={styles.btnSearch}
            onClick={() => navigate('/search')}
          >
            <Search size={14} />
            חפש טרמפ
          </button>
        </div>
      ) : (
        <>
          <div className={styles.grid}>
            {activeRequests.map((r) => (
              <div key={r.request_id} className={styles.cardWrap}>
                <button
                  type="button"
                  className={styles.cardDeleteBtn}
                  onClick={() => setRequestToCancel(r)}
                  aria-label="הסר בקשת טרמפ"
                  title="הסר בקשה"
                >
                  <X size={14} strokeWidth={2.5} />
                </button>
                <RideCard
                  route={`${r.pickup_name ?? '?'} ← ${r.destination_name ?? '?'}`}
                  scheduleCaption="זמן מבוקש לנסיעה"
                  time={formatDateTimeNoSeconds(r.requested_departure_time)}
                  status={statusLabels[r.status] || r.status}
                  source={getRideSourceLabel(r.group_id, myGroups)}
                />
              </div>
            ))}
          </div>
          {pastRequests.length > 0 ? (
            <HistorySection title="בקשות עבר">
              <div className={styles.grid}>
                {pastRequests.map((r) => (
                  <div key={r.request_id} className={styles.cardWrap}>
                    <RideCard
                      route={`${r.pickup_name ?? '?'} ← ${r.destination_name ?? '?'}`}
                      scheduleCaption="זמן מבוקש לנסיעה"
                      time={formatDateTimeNoSeconds(r.requested_departure_time)}
                      status={statusLabels[r.status] || r.status}
                      source={getRideSourceLabel(r.group_id, myGroups)}
                    />
                  </div>
                ))}
              </div>
            </HistorySection>
          ) : null}
        </>
      )}
      <ConfirmModal
        open={requestToCancel != null}
        onClose={() => setRequestToCancel(null)}
        title="האם אתה בטוח שאתה רוצה להסיר את בקשת הטרמפ הזו?"
        description="זה יבטל גם בקשות הצטרפות שנשלחו לנהגים (אם קיימות)."
        confirmLabel="אישור"
        variant="danger"
        loading={cancelling}
        onConfirm={confirmCancelRequest}
        titleId="confirm-cancel-request-title"
      />
    </div>
  );
}
