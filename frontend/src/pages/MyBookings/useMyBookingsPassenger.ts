import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { qk, mk } from '../../api/queryKeys';
import { useUserEvent } from '../../hooks/useUserEvent';
import { apiErr } from '../../utils/i18nError';
import { cancelPassengerBooking, fetchPassengerSummary } from '../../api/bookings';
import { getApiErrorMessage } from '../../utils/apiError';
import { useRideWebSocket } from '../../hooks/useRideWebSocket';
import type { RideEvent } from '../../types/wsEvents';
import type { PassengerBookingItem } from './myBookings.types';
import { LIVE_STATUSES } from '../../constants/rideStatuses';
import { mapPassengerSummaryToItems } from './myBookings.mappers';

/** Passenger mode: loading and booking cancellation. */
export function useMyBookingsPassenger(
  userId: string | undefined,
  setError: (message: string) => void
) {
  const queryClient = useQueryClient();
  const [bookingToCancel, setBookingToCancel] = useState<string | null>(null);
  const { data, isLoading: passengerLoading } = useQuery({
    queryKey: qk.bookings.passenger(userId),
    queryFn: async () => {
      const { data } = await fetchPassengerSummary();
      return mapPassengerSummaryToItems(data);
    },
    enabled: !!userId,
    staleTime: 30_000,
  });
  const passengerList = data ?? [];

  const cancelMutation = useMutation({
    mutationKey: mk.bookings.cancel('passenger'),
    mutationFn: (bookingId: string) => cancelPassengerBooking(bookingId),
    onSuccess: (_, bookingId) => {
      queryClient.setQueryData(
        qk.bookings.passenger(userId),
        (old: PassengerBookingItem[] = []) =>
          old.map((item) =>
            item.bookingId === bookingId
              ? { ...item, bookingStatus: 'cancelled' }
              : item
          )
      );
      setBookingToCancel(null);
    },
    onError: async (err) => {
      setError(getApiErrorMessage(err, apiErr('err_cancel_booking')));
      await queryClient.invalidateQueries({ queryKey: qk.bookings.passenger(userId) });
    },
  });

  useUserEvent(
    ['booking.approved_by_driver', 'booking.rejected_by_driver'],
    useCallback(() => {
      void queryClient.invalidateQueries({ queryKey: qk.bookings.passenger(userId) });
    }, [queryClient, userId])
  );

  useUserEvent(
    'BOOKING_COMPLETED',
    useCallback((detail) => {
      if (!detail.booking_id) return;
      queryClient.setQueryData(
        qk.bookings.passenger(userId),
        (old: PassengerBookingItem[] = []) =>
          old.map((item) =>
            item.bookingId === detail.booking_id
              ? { ...item, bookingStatus: 'completed' }
              : item
          )
      );
    }, [queryClient, userId])
  );

  // Subscribed while ride is still open/full/active so cancel/start/end events arrive; pick soonest departure when multiple confirmed.
  const watchedRideId =
    passengerList
      .filter(
        (item) =>
          item.bookingStatus === 'confirmed' && LIVE_STATUSES.has(item.ride.status)
      )
      .sort(
        (a, b) =>
          new Date(a.ride.departure_time).getTime() -
          new Date(b.ride.departure_time).getTime()
      )[0]?.ride.ride_id ?? null;

  useRideWebSocket({
    rideId: watchedRideId,
    enabled: !!watchedRideId,
    onMessage: useCallback(
      (msg: RideEvent) => {
        if (
          msg.event === 'RIDE_STARTED' ||
          msg.event === 'RIDE_CANCELLED' ||
          msg.event === 'RIDE_ENDED'
        ) {
          void queryClient.invalidateQueries({ queryKey: qk.bookings.passenger(userId) });
        }
      },
      [queryClient, userId]
    ),
  });

  const confirmCancelBooking = useCallback(() => {
    if (bookingToCancel) cancelMutation.mutate(bookingToCancel);
  }, [bookingToCancel, cancelMutation]);

  return {
    passengerList,
    passengerLoading,
    bookingToCancel,
    setBookingToCancel,
    cancelling: cancelMutation.isPending,
    confirmCancelBooking,
  };
}
