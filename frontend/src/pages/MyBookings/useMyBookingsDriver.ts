import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiErr } from '../../utils/i18nError';
import { useUserEvent } from '../../hooks/useUserEvent';
import { approveBooking, fetchDriverSummary, rejectBooking } from '../../api/bookings';
import { cancelRide, endRide, startRide } from '../../api/rides';
import { useLocationBroadcast } from '../../hooks/useLocationBroadcast';
import { getApiErrorCode, getApiErrorMessage, getApiStatus } from '../../utils/apiError';
import type { DriverBookingItem, TabKind } from './myBookings.types';
import { mapDriverSummaryToItems } from './myBookings.mappers';

type DriverStatus =
  | { kind: 'idle' }
  | { kind: 'loading'; busyBookingId?: string }
  | { kind: 'action'; bookingId: string };

/** Driver mode: loading, approvals, and location sharing. */
export function useMyBookingsDriver(
  user: { user_id: string } | null | undefined,
  activeTab: TabKind,
  setError: (message: string) => void
) {
  const userId = user?.user_id;
  const [driverList, setDriverList] = useState<DriverBookingItem[]>([]);
  const [driverStatus, setDriverStatus] = useState<DriverStatus>({ kind: 'idle' });
  const [sharingRideId, setSharingRideId] = useState<string | null>(null);
  const [liveRideId, setLiveRideId] = useState<string | null>(null);
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancellingRide, setCancellingRide] = useState(false);

  const fetchDriverBookings = useCallback(async (busyBookingId?: string) => {
    if (!userId) return;
    setDriverStatus(
      busyBookingId !== undefined ? { kind: 'loading', busyBookingId } : { kind: 'loading' }
    );
    setError('');
    try {
      const { data } = await fetchDriverSummary();
      setDriverList(mapDriverSummaryToItems(data));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_load_driver_bookings')));
    } finally {
      setDriverStatus({ kind: 'idle' });
    }
  }, [userId, setError]);

  useEffect(() => {
    if (activeTab === 'driver') void fetchDriverBookings();
  }, [activeTab, fetchDriverBookings]);

  useUserEvent(
    'booking.passenger_join_request',
    useCallback(() => {
      void fetchDriverBookings();
    }, [fetchDriverBookings])
  );

  useUserEvent(
    'RIDE_FINISHED',
    useCallback((detail) => {
      if (!detail.ride_id) return;
      setDriverList((prev) =>
        prev.map((item) =>
          item.ride.ride_id === detail.ride_id
            ? {
                ...item,
                ride: {
                  ...item.ride,
                  status: (detail.status as typeof item.ride.status) ?? 'completed',
                },
              }
            : item
        )
      );
    }, [])
  );

  const handleShareStart = useCallback(
    async (rideId: string) => {
      setError('');
      try {
        await startRide(rideId);
        await fetchDriverBookings();
      } catch (err: unknown) {
        const status = getApiStatus(err);
        const code = getApiErrorCode(err);
        const detail = getApiErrorMessage(err, '');
        if (status === 400 && (code === 'RIDE_INVALID_STATUS' || /active|ACTIVE|פעיל/i.test(detail))) {
          await fetchDriverBookings();
          return;
        }
        setError(detail || apiErr('err_start_ride'));
        throw err;
      }
    },
    [fetchDriverBookings, setError]
  );

  const handleShareStop = useCallback(
    async (rideId: string) => {
      try {
        await endRide(rideId);
        setLiveRideId((prev) => (prev === rideId ? null : prev));
      } catch (err: unknown) {
        const status = getApiStatus(err);
        if (status === 400) return;
        console.error('handleShareStop error:', err);
      } finally {
        await fetchDriverBookings();
      }
    },
    [fetchDriverBookings]
  );

  const driverShareConfirmedBookingId = useMemo(() => {
    if (!sharingRideId) return null;
    const block = driverList.find((d) => d.ride.ride_id === sharingRideId);
    return block?.passengers.find((p) => p.status === 'confirmed')?.bookingId ?? null;
  }, [sharingRideId, driverList]);

  useLocationBroadcast({
    rideId: sharingRideId,
    driverId: userId ?? null,
    bookingId: driverShareConfirmedBookingId,
    enabled: !!sharingRideId && !!userId && !!driverShareConfirmedBookingId,
    onStart: handleShareStart,
    onStop: handleShareStop,
  });

  const handleApprove = useCallback(
    async (bookingId: string) => {
      if (!userId) return;
      setDriverStatus({ kind: 'action', bookingId });
      setError('');
      try {
        await approveBooking(bookingId);
        await fetchDriverBookings(bookingId);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, apiErr('err_approve_booking')));
      } finally {
        setDriverStatus({ kind: 'idle' });
      }
    },
    [userId, fetchDriverBookings, setError]
  );

  const handleReject = useCallback(
    async (bookingId: string) => {
      if (!userId) return;
      setDriverStatus({ kind: 'action', bookingId });
      setError('');
      try {
        await rejectBooking(bookingId);
        await fetchDriverBookings(bookingId);
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, apiErr('err_reject_booking')));
      } finally {
        setDriverStatus({ kind: 'idle' });
      }
    },
    [userId, fetchDriverBookings, setError]
  );

  const confirmCancelRide = useCallback(async () => {
    if (rideToCancel == null) return;
    setCancellingRide(true);
    setError('');
    try {
      await cancelRide(rideToCancel);
      setDriverList((prev) =>
        prev.map((item) =>
          item.ride.ride_id === rideToCancel
            ? { ...item, ride: { ...item.ride, status: 'cancelled' } }
            : item
        )
      );
      if (sharingRideId === rideToCancel) setSharingRideId(null);
      setLiveRideId((prev) => (prev === rideToCancel ? null : prev));
      setRideToCancel(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_cancel_ride')));
      await fetchDriverBookings();
    } finally {
      setCancellingRide(false);
    }
  }, [rideToCancel, sharingRideId, fetchDriverBookings, setError]);

  const actionBookingIdForUi =
    driverStatus.kind === 'action'
      ? driverStatus.bookingId
      : driverStatus.kind === 'loading' && driverStatus.busyBookingId !== undefined
        ? driverStatus.busyBookingId
        : null;

  return {
    driverList,
    driverLoading: driverStatus.kind === 'loading',
    sharingRideId,
    setSharingRideId,
    liveRideId,
    setLiveRideId,
    rideToCancel,
    setRideToCancel,
    cancellingRide,
    actionBookingId: actionBookingIdForUi,
    handleShareStart,
    handleShareStop,
    handleApprove,
    handleReject,
    confirmCancelRide,
  };
}
