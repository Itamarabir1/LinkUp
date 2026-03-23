import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Car, Plus } from 'lucide-react';
import { api } from '../api/client';
import type { Ride } from '../types/api';
import { formatDateTimeNoSeconds } from '../utils/date';
import { getWsBaseUrl } from '../config/env';
import { useAuth } from '../context/AuthContext';
import { useGroup } from '../context/GroupContext';
import Chips, { type ChipItem } from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import styles from './MyRides.module.css';

const getRideWsUrl = (rideId: string): string =>
  `${getWsBaseUrl()}/rides/ws/${rideId}`;

function getStatusLabel(r: Ride): string {
  if (r.status === 'cancelled') return 'בוטלה';
  if (r.status === 'active') return 'פעילה';
  const seats = r.available_seats ?? 0;
  if (seats <= 0) return 'מלא';
  if (seats === 1) return '1 מקום';
  return `${seats} מקומות`;
}

export default function MyRides() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { myGroups } = useGroup();
  const [rides, setRides] = useState<Ride[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeChip, setActiveChip] = useState<string>('all');
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const wsRefs = useRef<Map<string, WebSocket>>(new Map());

  const chipItems: ChipItem[] = [
    { id: 'all', label: 'הכל' },
    { id: 'public', label: 'ציבורי' },
    ...myGroups.map((g) => ({ id: g.group_id, label: g.name })),
  ];

  const displayedRides = rides.filter((r) => {
    if (activeChip === 'all') return true;
    if (activeChip === 'public') return !r.group_id;
    return r.group_id === activeChip;
  });

  const getSource = (r: Ride): string => {
    if (!r.group_id) return 'ציבורי';
    const g = myGroups.find((x) => x.group_id === r.group_id);
    return g?.name ?? 'ציבורי';
  };

  const fetchRides = useCallback(async () => {
    try {
      const { data } = await api.get<Ride[]>('/rides/me');
      const active = (Array.isArray(data) ? data : []).filter(
        (r) => r.status !== 'cancelled'
      );
      setRides(active);
      setError('');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'טעינת נסיעות נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setLoading(false);
    }
  }, [user?.user_id]);

  useEffect(() => {
    fetchRides();
  }, [fetchRides]);

  useEffect(() => {
    const rideIds = rides.map((r) => r.ride_id);
    const currentIds = new Set(rideIds);
    rideIds.forEach((rideId) => {
      if (wsRefs.current.has(rideId)) return;
      const url = getRideWsUrl(rideId);
      try {
        const ws = new WebSocket(url);
        wsRefs.current.set(rideId, ws);
        ws.onmessage = (ev) => {
          try {
            const payload = JSON.parse(ev.data as string) as { event?: string };
            if (payload.event === 'RIDE_CANCELLED') {
              setRides((prev) => prev.filter((r) => r.ride_id !== rideId));
            }
          } catch {
            // ignore
          }
        };
        ws.onclose = () => wsRefs.current.delete(rideId);
      } catch {
        wsRefs.current.delete(rideId);
      }
    });
    wsRefs.current.forEach((sock, id) => {
      if (!currentIds.has(id)) {
        sock.close();
        wsRefs.current.delete(id);
      }
    });
  }, [rides]);

  useEffect(() => {
    return () => {
      wsRefs.current.forEach((sock) => sock.close());
      wsRefs.current.clear();
    };
  }, []);

  const handleConfirmCancel = useCallback(async () => {
    if (rideToCancel == null) return;
    setCancelling(true);
    setError('');
    try {
      await api.delete(`/rides/${rideToCancel}/cancel`);
      setRides((prev) => prev.filter((r) => r.ride_id !== rideToCancel));
      setRideToCancel(null);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'ביטול הנסיעה נכשל';
      setError(typeof msg === 'string' ? msg : String(msg));
      setRideToCancel(null);
    } finally {
      setCancelling(false);
    }
  }, [rideToCancel]);

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

      {rides.length === 0 ? (
        <div className={styles.emptyState}>
          <Car size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>אין נסיעות עדיין</h2>
          <p className={styles.emptySubtitle}>צור את הנסיעה הראשונה שלך</p>
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={() => navigate('/create-ride')}
          >
            <Plus size={14} />
            הצע נסיעה
          </button>
        </div>
      ) : (
        <div className={styles.grid}>
          {displayedRides.map((r) => (
            <div key={r.ride_id} className={styles.cardWrap}>
              <button
                type="button"
                className={styles.cardDeleteBtn}
                onClick={(e) => {
                  e.stopPropagation();
                  setRideToCancel(r.ride_id);
                }}
                title="מחק נסיעה"
                aria-label="מחק נסיעה"
              >
                ×
              </button>
              <RideCard
                route={`${r.origin_name ?? '?'} ← ${r.destination_name ?? '?'}`}
                scheduleCaption="זמן הנסיעה"
                time={formatDateTimeNoSeconds(r.departure_time)}
                status={getStatusLabel(r)}
                source={getSource(r)}
              />
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={rideToCancel != null}
        onClose={() => setRideToCancel(null)}
        title="האם אתה בטוח שאתה רוצה לבטל את הנסיעה?"
        confirmLabel="אישור"
        variant="danger"
        loading={cancelling}
        onConfirm={handleConfirmCancel}
        titleId="confirm-cancel-ride-title"
      />

    </div>
  );
}
