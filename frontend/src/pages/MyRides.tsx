import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Car, Plus, X } from 'lucide-react';
import { cancelRide, fetchMyRides } from '../api/rides';
import type { Ride } from '../types/api';
import { formatDateTimeNoSeconds } from '../utils/date';
import { useGroup } from '../context/GroupContext';
import Chips, { type ChipItem } from '../components/Chips/Chips';
import RideCard from '../components/RideCard/RideCard';
import ConfirmModal from '../components/ConfirmModal/ConfirmModal';
import ErrorBanner from '../components/ErrorBanner';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { getRideSourceLabel, getRideStatusLabel } from '../utils/rideDisplay';
import HistorySection from '../components/HistorySection/HistorySection';
import { useUserEvent } from '../hooks/useUserEvent';
import { useRideWebSocket } from '../hooks/useRideWebSocket';
import { LIVE_STATUSES } from '../constants/rideStatuses';
import styles from './MyRides.module.css';

export default function MyRides() {
  const { t } = useTranslation(['rides', 'common']);
  const navigate = useNavigate();
  const { myGroups, activeChipId, setActiveChipId } = useGroup();
  const [rides, setRides] = useState<Ride[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const chipItems: ChipItem[] = [
    { id: 'all', label: t('common:all') },
    { id: 'public', label: t('common:public') },
    ...myGroups.map((g) => ({ id: g.group_id, label: g.name })),
  ];

  const displayedRides = rides.filter((r) => {
    if (activeChipId === 'all') return true;
    if (activeChipId === 'public') return !r.group_id;
    return r.group_id === activeChipId;
  });
  const activeRides = displayedRides.filter(
    (r) => r.status !== 'cancelled' && r.status !== 'completed'
  );
  const pastRides = displayedRides.filter(
    (r) => r.status === 'cancelled' || r.status === 'completed'
  );

  // One WS slot: prefer the soonest departing live ride so updates match the trip the user cares about first.
  const watchedRideId =
    rides
      .filter((r) => LIVE_STATUSES.has(r.status))
      .sort(
        (a, b) =>
          new Date(a.departure_time).getTime() - new Date(b.departure_time).getTime()
      )[0]?.ride_id ?? null;

  const fetchRides = useCallback(async () => {
    try {
      const { data } = await fetchMyRides();
      setRides(Array.isArray(data) ? data : []);
      setError('');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_load_rides')));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRides();
  }, [fetchRides]);

  // Real-time updates from the user event stream (driver-owned events).
  useUserEvent(
    ['RIDE_FINISHED', 'RIDE_CANCELLED'],
    useCallback(
      (detail) => {
        if (!detail.ride_id) return;
        setRides((prev) =>
          prev.map((r) =>
            r.ride_id === detail.ride_id
              ? { ...r, status: (detail.status as Ride['status']) ?? 'completed' }
              : r
          )
        );
      },
      []
    )
  );

  // Per-ride WS for the single live ride — catches RIDE_STARTED / RIDE_ENDED / RIDE_CANCELLED.
  useRideWebSocket({
    rideId: watchedRideId,
    enabled: !!watchedRideId,
    onMessage: useCallback(
      (msg) => {
        if (
          msg.event === 'RIDE_CANCELLED' ||
          msg.event === 'RIDE_ENDED' ||
          msg.event === 'RIDE_STARTED'
        ) {
          void fetchRides();
        }
      },
      [fetchRides]
    ),
  });

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
      setError(getApiErrorMessage(err, apiErr('err_cancel_ride')));
      setRideToCancel(null);
    } finally {
      setCancelling(false);
    }
  }, [rideToCancel]);

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.pageLoading}>{t('common:loading')}</div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Chips items={chipItems} activeId={activeChipId} onChange={setActiveChipId} />

      {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}

      {displayedRides.length === 0 ? (
        <div className={styles.emptyState}>
          <Car size={48} strokeWidth={1.5} className={styles.emptyIcon} />
          <h2 className={styles.emptyTitle}>{t('rides:noRides')}</h2>
          <p className={styles.emptySubtitle}>{t('rides:createFirstRide')}</p>
          <button
            type="button"
            className={styles.btnPrimary}
            onClick={() => navigate('/create-ride')}
          >
            <Plus size={14} />
            {t('rides:createRide')}
          </button>
        </div>
      ) : (
        <>
          {activeRides.length > 0 && (
            <>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionLabel}>{t('rides:activeRides')}</span>
                <span className={styles.sectionCount}>{t('rides:activeRidesCount', { count: activeRides.length })}</span>
              </div>
              <div className={styles.gridWrap}>
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
                        title={t('rides:cancelRide')}
                        aria-label={t('rides:cancelRide')}
                      >
                        <X size={12} strokeWidth={2.5} />
                      </button>
                      <RideCard
                        originLabel={r.origin_name ?? '?'}
                        destinationLabel={r.destination_name ?? '?'}
                        scheduleCaption={t('rides:rideTimeLabel')}
                        time={formatDateTimeNoSeconds(r.departure_time)}
                        status={getRideStatusLabel(r)}
                        source={getRideSourceLabel(r.group_id, myGroups)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {pastRides.length > 0 && (
            <div className={styles.gridWrap}>
              <HistorySection title={t('rides:pastRidesCount', { count: pastRides.length })}>
                <div className={styles.grid}>
                  {pastRides.map((r) => (
                    <div key={r.ride_id} className={styles.cardWrap}>
                      <RideCard
                        originLabel={r.origin_name ?? '?'}
                        destinationLabel={r.destination_name ?? '?'}
                        scheduleCaption={t('rides:rideTimeLabel')}
                        time={formatDateTimeNoSeconds(r.departure_time)}
                        status={getRideStatusLabel(r)}
                        source={getRideSourceLabel(r.group_id, myGroups)}
                      />
                    </div>
                  ))}
                </div>
              </HistorySection>
            </div>
          )}
        </>
      )}

      <ConfirmModal
        open={rideToCancel != null}
        onClose={() => setRideToCancel(null)}
        title={t('rides:confirmCancelRide')}
        confirmLabel={t('common:confirm')}
        variant="danger"
        loading={cancelling}
        onConfirm={handleConfirmCancel}
        titleId="confirm-cancel-ride-title"
      />
    </div>
  );
}
