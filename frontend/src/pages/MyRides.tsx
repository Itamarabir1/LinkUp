import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Car, Plus } from 'lucide-react';
import { cancelRide, fetchMyRides } from '../api/rides';
import type { Ride } from '../types/api';
import { formatDateTimeNoSeconds } from '../utils/date';
import { STORAGE_KEYS } from '../config/constants';
import { WS_URLS } from '../config/wsUrls';
import { RideEventSchema } from '../types/wsEvents';
import { useGroup } from '../context/GroupContext';
import Chips, { type ChipItem } from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../components/ErrorBanner';
import { getApiErrorMessage } from '../utils/apiError';
import { getRideSourceLabel } from '../utils/rideDisplay';
import HistorySection from '../components/HistorySection/HistorySection';
import styles from './MyRides.module.css';

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
  const { myGroups, activeChipId, setActiveChipId } = useGroup();
  const [rides, setRides] = useState<Ride[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const wsRefs = useRef<Map<string, WebSocket>>(new Map());
  const ridesRef = useRef<Ride[]>([]);
  ridesRef.current = rides;

  const chipItems: ChipItem[] = [
    { id: 'all', label: 'הכל' },
    { id: 'public', label: 'ציבורי' },
    ...myGroups.map((g) => ({ id: g.group_id, label: g.name })),
  ];

  const displayedRides = rides.filter((r) => {
    if (activeChipId === 'all') return true;
    if (activeChipId === 'public') return !r.group_id;
    return r.group_id === activeChipId;
  });
  const activeRides = displayedRides.filter((r) => r.status !== 'cancelled' && r.status !== 'completed');
  const pastRides = displayedRides.filter((r) => r.status === 'cancelled' || r.status === 'completed');

  const fetchRides = useCallback(async () => {
    try {
      const { data } = await fetchMyRides();
      setRides(Array.isArray(data) ? data : []);
      setError('');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינת נסיעות נכשלה'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRides();
  }, [fetchRides]);

  useEffect(() => {
    const onUserEvent = (evt: Event) => {
      const detail = (evt as CustomEvent<{ event?: string; ride_id?: string; status?: string }>).detail;
      if (!detail?.event || !detail.ride_id) return;
      if (detail.event === 'RIDE_FINISHED' || detail.event === 'RIDE_CANCELLED') {
        setRides((prev) =>
          prev.map((r) =>
            r.ride_id === detail.ride_id ? { ...r, status: (detail.status as Ride['status']) ?? 'completed' } : r
          )
        );
      }
    };
    window.addEventListener('linkup:user-event', onUserEvent as EventListener);
    return () => window.removeEventListener('linkup:user-event', onUserEvent as EventListener);
  }, []);

  useEffect(() => {
    const rideIds = rides.map((r) => r.ride_id);
    const currentIds = new Set(rideIds);
    const token = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    if (!token) return;

    const handleMessage = (_rideId: string, ev: MessageEvent) => {
      try {
        const raw = JSON.parse(ev.data as string);
        const result = RideEventSchema.safeParse(raw);
        if (!result.success) return;
        const { event } = result.data;
        if (
          event === 'RIDE_CANCELLED' ||
          event === 'RIDE_ENDED' ||
          event === 'RIDE_STARTED'
        ) {
          void fetchRides();
        }
      } catch {
        /* ignore */
      }
    };

    const openWs = (rideId: string) => {
      if (wsRefs.current.has(rideId)) return;
      try {
        const ws = new WebSocket(WS_URLS.ride(rideId, token));
        wsRefs.current.set(rideId, ws);
        ws.onmessage = (ev) => handleMessage(rideId, ev);
        ws.onclose = () => {
          wsRefs.current.delete(rideId);
          if (ridesRef.current.some((r) => r.ride_id === rideId)) {
            setTimeout(() => {
              if (wsRefs.current.has(rideId)) return;
              if (!ridesRef.current.some((r) => r.ride_id === rideId)) return;
              openWs(rideId);
            }, 3000);
          }
        };
        ws.onerror = () => ws.close();
      } catch {
        wsRefs.current.delete(rideId);
      }
    };

    rideIds.forEach((rideId) => openWs(rideId));
    wsRefs.current.forEach((sock, id) => {
      if (!currentIds.has(id)) {
        sock.close();
        wsRefs.current.delete(id);
      }
    });
  }, [rides, fetchRides]);

  useEffect(() => {
    const refs = wsRefs.current;
    return () => {
      refs.forEach((sock) => sock.close());
      refs.clear();
    };
  }, []);

  const handleConfirmCancel = useCallback(async () => {
    if (rideToCancel == null) return;
    setCancelling(true);
    setError('');
    try {
      await cancelRide(rideToCancel);
      setRides((prev) =>
        prev.map((r) => (r.ride_id === rideToCancel ? { ...r, status: 'cancelled' } : r))
      );
      setRideToCancel(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'ביטול הנסיעה נכשל'));
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
        activeId={activeChipId}
        onChange={setActiveChipId}
      />
      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

      {displayedRides.length === 0 ? (
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
        <>
          <div className={styles.grid}>
            {activeRides.map((r) => (
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
                  source={getRideSourceLabel(r.group_id, myGroups)}
                />
              </div>
            ))}
          </div>
          {pastRides.length > 0 ? (
            <HistorySection title="נסיעות עבר">
              <div className={styles.grid}>
                {pastRides.map((r) => (
                  <div key={r.ride_id} className={styles.cardWrap}>
                    <RideCard
                      route={`${r.origin_name ?? '?'} ← ${r.destination_name ?? '?'}`}
                      scheduleCaption="זמן הנסיעה"
                      time={formatDateTimeNoSeconds(r.departure_time)}
                      status={getStatusLabel(r)}
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
