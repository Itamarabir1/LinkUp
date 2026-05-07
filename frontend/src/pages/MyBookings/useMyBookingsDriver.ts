import { useCallback, useMemo, useState } from 'react';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk, mk } from '../../api/queryKeys';
import { apiErr } from '../../utils/i18nError';
import { useUserEvent } from '../../hooks/useUserEvent';
import {
  approveBooking,
  fetchDriverActive,
  fetchDriverHistory,
  rejectBooking,
} from '../../api/bookings';
import { cancelRide, endRide, startRide } from '../../api/rides';
import { useLocationBroadcast } from '../../hooks/useLocationBroadcast';
import { getApiErrorCode, getApiErrorMessage, getApiStatus } from '../../utils/apiError';
import type { TabKind } from './myBookings.types';
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

  const invalidateDriverCaches = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: qk.bookings.driverActive(userId) }),
      queryClient.invalidateQueries({ queryKey: qk.bookings.driverHistory(userId) }),
    ]);
  }, [queryClient, userId]);

  const enabled = activeTab === 'driver' && !!userId;

  const activeQuery = useQuery({
    queryKey: qk.bookings.driverActive(userId),
    queryFn: async () => {
      const { data } = await fetchDriverActive();
      return mapDriverSummaryToItems(data);
    },
    enabled,
    staleTime: 30_000,
  });

  const historyQuery = useInfiniteQuery({
    queryKey: qk.bookings.driverHistory(userId),
    queryFn: async ({ pageParam }) => {
      const { data } = await fetchDriverHistory({ limit: 20, after: pageParam ?? undefined });
      return data;
    },
    enabled,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 30_000,
  });
  const fetchNextDriverHistory = historyQuery.fetchNextPage;
  const hasNextDriverHistory = historyQuery.hasNextPage;

  const activeItems = useMemo(() => activeQuery.data ?? [], [activeQuery.data]);

  const historyItems = useMemo(
    () =>
      historyQuery.data?.pages.flatMap((page) => mapDriverSummaryToItems({ rides: page.rides })) ??
      [],
    [historyQuery.data?.pages],
  );

  const driverLoading =
    activeQuery.isLoading || (historyQuery.isLoading && !historyQuery.data);

  const { mutate: approveBookingMutation } = useMutation({
    mutationKey: mk.bookings.approve(''),
    mutationFn: async (bookingId: string) => {
      setDriverStatus({ kind: 'action', bookingId });
      await approveBooking(bookingId);
    },
    onSuccess: invalidateDriverCaches,
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
    onSuccess: invalidateDriverCaches,
    onError: (err) => {
      setError(getApiErrorMessage(err, apiErr('err_reject_booking')));
    },
    onSettled: () => setDriverStatus({ kind: 'idle' }),
  });

  useUserEvent(
    'booking.passenger_join_request',
    useCallback(() => {
      void invalidateDriverCaches();
    }, [invalidateDriverCaches]),
  );

  useUserEvent(
    'RIDE_FINISHED',
    useCallback((detail) => {
      if (!detail.ride_id) return;
      void invalidateDriverCaches();
    }, [invalidateDriverCaches]),
  );

  const handleShareStart = useCallback(
    async (rideId: string) => {
      setError('');
      try {
        await startRide(rideId);
        await invalidateDriverCaches();
      } catch (err: unknown) {
        const status = getApiStatus(err);
        const code = getApiErrorCode(err);
        const detail = getApiErrorMessage(err, '');
        if (status === 400 && (code === 'RIDE_INVALID_STATUS' || /active|ACTIVE|פעיל/i.test(detail))) {
          await invalidateDriverCaches();
          return;
        }
        setError(detail || apiErr('err_start_ride'));
        throw err;
      }
    },
    [invalidateDriverCaches, setError],
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
        await invalidateDriverCaches();
      }
    },
    [invalidateDriverCaches],
  );

  const driverShareConfirmedBookingId = useMemo(() => {
    if (!sharingRideId) return null;
    const block = activeItems.find((d) => d.ride.ride_id === sharingRideId);
    return block?.passengers.find((p) => p.status === 'confirmed')?.bookingId ?? null;
  }, [sharingRideId, activeItems]);

  useLocationBroadcast({
    rideId: sharingRideId,
    driverId: userId ?? null,
    bookingId: driverShareConfirmedBookingId,
    enabled: !!sharingRideId && !!userId && !!driverShareConfirmedBookingId,
    onStart: handleShareStart,
    onStop: handleShareStop,
  });

  const handleApprove = useCallback(
    (bookingId: string) => {
      if (!userId) return;
      approveBookingMutation(bookingId);
    },
    [approveBookingMutation, userId],
  );

  const handleReject = useCallback(
    (bookingId: string) => {
      if (!userId) return;
      rejectBookingMutation(bookingId);
    },
    [rejectBookingMutation, userId],
  );

  const confirmCancelRide = useCallback(async () => {
    if (rideToCancel == null) return;
    setCancellingRide(true);
    setError('');
    try {
      await cancelRide(rideToCancel);
      await invalidateDriverCaches();
      if (sharingRideId === rideToCancel) setSharingRideId(null);
      setLiveRideId((prev) => (prev === rideToCancel ? null : prev));
      setRideToCancel(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_cancel_ride')));
      await invalidateDriverCaches();
    } finally {
      setCancellingRide(false);
    }
  }, [rideToCancel, sharingRideId, invalidateDriverCaches, setError]);

  const fetchMoreDriverHistory = useCallback(() => {
    if (hasNextDriverHistory) void fetchNextDriverHistory();
  }, [fetchNextDriverHistory, hasNextDriverHistory]);

  const actionBookingIdForUi =
    driverStatus.kind === 'action'
      ? driverStatus.bookingId
      : driverStatus.kind === 'loading' && driverStatus.busyBookingId !== undefined
        ? driverStatus.busyBookingId
        : null;

  return {
    activeItems,
    historyItems,
    driverLoading,
    fetchMoreDriverHistory,
    hasMoreDriverHistory: hasNextDriverHistory ?? false,
    isFetchingDriverHistory: historyQuery.isFetchingNextPage,
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
