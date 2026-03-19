import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { api } from '../api/client';
import type { PassengerRequest } from '../types/api';
import { formatRideDate } from '../utils/date';
import { useGroup } from '../context/GroupContext';
import Chips, { type ChipItem } from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
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
  const { myGroups } = useGroup();
  const [requests, setRequests] = useState<PassengerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeChip, setActiveChip] = useState<string>('all');
  const [requestToCancel, setRequestToCancel] = useState<PassengerRequest | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const chipItems: ChipItem[] = [
    { id: 'all', label: 'הכל' },
    { id: 'public', label: 'ציבורי' },
    ...myGroups.map((g) => ({ id: g.group_id, label: g.name })),
  ];

  const displayedRequests = requests.filter((r) => {
    if (activeChip === 'all') return true;
    if (activeChip === 'public') return !r.group_id;
    return r.group_id === activeChip;
  });

  const getSource = (r: PassengerRequest): string => {
    if (!r.group_id) return 'ציבורי';
    const g = myGroups.find((x) => x.group_id === r.group_id);
    return g?.name ?? 'ציבורי';
  };

  const fetchRequests = useCallback(async () => {
    try {
      const { data } = await api.get<PassengerRequest[]>(
        '/passenger/passengers/me'
      );
      const all = Array.isArray(data) ? data : [];
      setRequests(all.filter((r) => r.status !== 'cancelled'));
      setError('');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'טעינת בקשות נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>טוען...</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Chips
        items={chipItems}
        activeId={activeChip}
        onChange={setActiveChip}
      />
      {error && <p className={styles.pageError}>{error}</p>}

      {requests.length === 0 ? (
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
        <div className={styles.grid}>
          {displayedRequests.map((r) => (
            <div key={r.request_id} className={styles.cardWrap}>
              <button
                type="button"
                className={styles.cardDeleteBtn}
                onClick={() => setRequestToCancel(r)}
                aria-label="הסר בקשת טרמפ"
                title="הסר בקשה"
              >
                ×
              </button>
              <RideCard
                route={`${r.pickup_name ?? '?'} ← ${r.destination_name ?? '?'}`}
                time={formatRideDate(r.requested_departure_time)}
                status={statusLabels[r.status] || r.status}
                source={getSource(r)}
              />
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={requestToCancel != null}
        onClose={() => setRequestToCancel(null)}
        title="האם אתה בטוח שאתה רוצה להסיר את בקשת הטרמפ הזו?"
        description="זה יבטל גם בקשות הצטרפות שנשלחו לנהגים (אם קיימות)."
        confirmLabel="אישור"
        variant="danger"
        loading={cancelling}
        onConfirm={async () => {
          if (!requestToCancel) return;
          setCancelling(true);
          setError('');
          try {
            await api.delete(
              `/passenger/passengers/${requestToCancel.request_id}/cancel`
            );
            setRequests((prev) =>
              prev.filter((p) => p.request_id !== requestToCancel.request_id)
            );
            setRequestToCancel(null);
          } catch (err: unknown) {
            const msg =
              (err as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail || 'ביטול הבקשה נכשל';
            setError(typeof msg === 'string' ? msg : String(msg));
          } finally {
            setCancelling(false);
          }
        }}
        titleId="confirm-cancel-request-title"
      />
    </div>
  );
}
