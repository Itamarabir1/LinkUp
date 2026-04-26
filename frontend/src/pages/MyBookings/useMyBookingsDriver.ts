import { useCallback, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk, mk } from '../../api/queryKeys';
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
  const queryClient = useQueryClient();
  const [driverStatus, setDriverStatus] = useState<DriverStatus>({ kind: 'idle' });
  const [sharingRideId, setSharingRideId] = useState<string | null>(null);
  const [liveRideId, setLiveRideId] = useState<string | null>(null);
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancellingRide, setCancellingRide] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: qk.bookings.driver(userId),
    queryFn: async () => {
      const { data } = await fetchDriverSummary();
      return mapDriverSummaryToItems(data);
    },
    enabled: activeTab === 'driver' && !!userId,
    staleTime: 30_000,
  });
  const driverList = useMemo(() => data ?? [], [data]);
  const driverLoading = isLoading;

  const { mutate: approveBookingMutation } = useMutation({
    mutationKey: mk.bookings.approve(''),
    mutationFn: async (bookingId: string) => {
      setDriverStatus({ kind: 'action', bookingId });
      await approveBooking(bookingId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
    },
    onError: (err) => {
      setError(getApiErrorMessage(err, apiErr('err_approve_booking')));
    },
    onSettled: () => setDriverStatus({ kind: 'idle' }),
  });

  const { mutate: rejectBookingMutation } = useMutation({
    mutationKey: mk.bookings.reject(''),
    mutationFn: async (bookingId: string) => {
      setDriverStatus({ kind: 'action', bookingId });
      await rejectBooking(bookingId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
    },
    onError: (err) => {
      setError(getApiErrorMessage(err, apiErr('err_reject_booking')));
    },
    onSettled: () => setDriverStatus({ kind: 'idle' }),
  });

  useUserEvent(
    'booking.passenger_join_request',
    useCallback(() => {
      void queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
    }, [queryClient, userId])
  );

  useUserEvent(
    'RIDE_FINISHED',
    useCallback((detail) => {
      if (!detail.ride_id) return;
      void queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
    }, [queryClient, userId])
  );

  const handleShareStart = useCallback(
    async (rideId: string) => {
      setError('');
      try {
        await startRide(rideId);
        await queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
      } catch (err: unknown) {
        const status = getApiStatus(err);
        const code = getApiErrorCode(err);
        const detail = getApiErrorMessage(err, '');
        if (status === 400 && (code === 'RIDE_INVALID_STATUS' || /active|ACTIVE|פעיל/i.test(detail))) {
          await queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
          return;
        }
        setError(detail || apiErr('err_start_ride'));
        throw err;
      }
    },
    [queryClient, setError, userId]
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
        await queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
      }
    },
    [queryClient, userId]
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

  const handleApprove = useCallback((bookingId: string) => {
    if (!userId) return;
    approveBookingMutation(bookingId);
  }, [approveBookingMutation, userId]);

  const handleReject = useCallback((bookingId: string) => {
    if (!userId) return;
    rejectBookingMutation(bookingId);
  }, [rejectBookingMutation, userId]);

  const confirmCancelRide = useCallback(async () => {
    if (rideToCancel == null) return;
    setCancellingRide(true);
    setError('');
    try {
      await cancelRide(rideToCancel);
      queryClient.setQueryData(
        qk.bookings.driver(userId),
        (old: DriverBookingItem[] = []) =>
          old.map((item) =>
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
      await queryClient.invalidateQueries({ queryKey: qk.bookings.driver(userId) });
    } finally {
      setCancellingRide(false);
    }
  }, [rideToCancel, sharingRideId, queryClient, userId, setError]);

  const actionBookingIdForUi =
    driverStatus.kind === 'action'
      ? driverStatus.bookingId
      : driverStatus.kind === 'loading' && driverStatus.busyBookingId !== undefined
        ? driverStatus.busyBookingId
        : null;

  return {
    driverList,
    driverLoading,
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
