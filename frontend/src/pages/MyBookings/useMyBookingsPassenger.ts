import { useCallback, useMemo, useState } from 'react';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk, mk } from '../../api/queryKeys';
import { useUserEvent } from '../../hooks/useUserEvent';
import { apiErr } from '../../utils/i18nError';
import {
  cancelPassengerBooking,
  fetchPassengerActive,
  fetchPassengerHistory,
} from '../../api/bookings';
import { getApiErrorMessage } from '../../utils/apiError';
import { useRideWebSocket } from '../../hooks/useRideWebSocket';
import type { RideEvent } from '../../types/wsEvents';
import type { TabKind } from './myBookings.types';
import { LIVE_STATUSES } from '../../constants/rideStatuses';
import { mapPassengerSummaryToItems } from './myBookings.mappers';

/** Ride WS while booking is alive (not pending/rejected-only). */
const WATCH_BOOKING_STATUSES = new Set([
  'confirmed',
  'en_route',
  'arrived',
  'trip_in_progress',
]);

/** Passenger mode: active + paginated history. */
export function useMyBookingsPassenger(
  userId: string | undefined,
  activeTab: TabKind,
  setError: (message: string) => void
) {
  const queryClient = useQueryClient();

  const invalidatePassengerCaches = useCallback(async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: qk.bookings.passengerActive(userId) }),
      queryClient.invalidateQueries({ queryKey: qk.bookings.passengerHistory(userId) }),
    ]);
  }, [queryClient, userId]);

  const enabled = activeTab === 'passenger' && !!userId;

  const activeQuery = useQuery({
    queryKey: qk.bookings.passengerActive(userId),
    queryFn: async () => {
      const { data } = await fetchPassengerActive();
      return mapPassengerSummaryToItems(data);
    },
    enabled,
    staleTime: 30_000,
  });

  const historyQuery = useInfiniteQuery({
    queryKey: qk.bookings.passengerHistory(userId),
    queryFn: async ({ pageParam }) => {
      const { data } = await fetchPassengerHistory({ limit: 20, after: pageParam ?? undefined });
      return data;
    },
    enabled,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 30_000,
  });
  const fetchNextPassengerHistory = historyQuery.fetchNextPage;
  const hasNextPassengerHistory = historyQuery.hasNextPage;

  const activeItems = useMemo(() => activeQuery.data ?? [], [activeQuery.data]);

  const historyItems = useMemo(
    () =>
      historyQuery.data?.pages.flatMap((page) => mapPassengerSummaryToItems({ bookings: page.bookings })) ??
      [],
    [historyQuery.data?.pages],
  );

  const passengerLoading =
    activeQuery.isLoading || (historyQuery.isLoading && !historyQuery.data);

  const fetchMorePassengerHistory = useCallback(() => {
    if (hasNextPassengerHistory) void fetchNextPassengerHistory();
  }, [fetchNextPassengerHistory, hasNextPassengerHistory]);

  const [bookingToCancel, setBookingToCancel] = useState<string | null>(null);

  const { mutate: cancelPassengerBookingMutation, isPending: isCancellingPassengerBooking } =
    useMutation({
      mutationKey: mk.bookings.cancel('passenger'),
      mutationFn: (bookingId: string) => cancelPassengerBooking(bookingId),
      onSuccess: async () => {
        setBookingToCancel(null);
        await invalidatePassengerCaches();
      },
      onError: async (err) => {
        setError(getApiErrorMessage(err, apiErr('err_cancel_booking')));
        await invalidatePassengerCaches();
      },
    });

  useUserEvent(
    ['booking.approved_by_driver', 'booking.rejected_by_driver'],
    useCallback(() => {
      void invalidatePassengerCaches();
    }, [invalidatePassengerCaches]),
  );

  useUserEvent(
    'BOOKING_COMPLETED',
    useCallback(() => void invalidatePassengerCaches(), [invalidatePassengerCaches]),
  );

  const watchedRideId =
    activeItems
      .filter(
        (item) =>
          WATCH_BOOKING_STATUSES.has(item.bookingStatus) &&
          LIVE_STATUSES.has(item.ride.status),
      )
      .sort(
        (a, b) =>
          new Date(a.ride.departure_time).getTime() - new Date(b.ride.departure_time).getTime(),
      )[0]?.ride.ride_id ?? null;

  useRideWebSocket({
    rideId: watchedRideId,
    enabled: !!watchedRideId,
    onMessage: useCallback(
      (msg: RideEvent) => {
        if (msg.event === 'RIDE_STARTED' || msg.event === 'RIDE_CANCELLED' || msg.event === 'RIDE_ENDED') {
          void invalidatePassengerCaches();
        }
      },
      [invalidatePassengerCaches],
    ),
  });

  const confirmCancelBooking = useCallback(() => {
    if (bookingToCancel) cancelPassengerBookingMutation(bookingToCancel);
  }, [bookingToCancel, cancelPassengerBookingMutation]);

  return {
    activeItems,
    historyItems,
    passengerLoading,
    fetchMorePassengerHistory,
    hasMorePassengerHistory: hasNextPassengerHistory ?? false,
    isFetchingPassengerHistory: historyQuery.isFetchingNextPage,
    bookingToCancel,
    setBookingToCancel,
    cancelling: isCancellingPassengerBooking,
    confirmCancelBooking,
  };
}
