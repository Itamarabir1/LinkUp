import { useCallback, useEffect, useState } from 'react';
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
  const [passengerList, setPassengerList] = useState<PassengerBookingItem[]>([]);
  const [passengerLoading, setPassengerLoading] = useState(true);
  const [bookingToCancel, setBookingToCancel] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const fetchPassengerBookings = useCallback(async () => {
    if (!userId) return;
    setPassengerLoading(true);
    setError('');
    try {
      const { data } = await fetchPassengerSummary();
      setPassengerList(mapPassengerSummaryToItems(data));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_load_passenger_bookings')));
    } finally {
      setPassengerLoading(false);
    }
  }, [userId, setError]);

  useEffect(() => {
    void fetchPassengerBookings();
  }, [fetchPassengerBookings]);

  useUserEvent(
    ['booking.approved_by_driver', 'booking.rejected_by_driver'],
    useCallback(() => {
      void fetchPassengerBookings();
    }, [fetchPassengerBookings])
  );

  useUserEvent(
    'BOOKING_COMPLETED',
    useCallback((detail) => {
      if (!detail.booking_id) return;
      setPassengerList((prev) =>
        prev.map((item) =>
          item.bookingId === detail.booking_id
            ? { ...item, bookingStatus: 'completed' }
            : item
        )
      );
    }, [])
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

  const onRideStatusMessage = useCallback(
    (msg: RideEvent) => {
      if (
        msg.event === 'RIDE_STARTED' ||
        msg.event === 'RIDE_CANCELLED' ||
        msg.event === 'RIDE_ENDED'
      ) {
        void fetchPassengerBookings();
      }
    },
    [fetchPassengerBookings]
  );

  useRideWebSocket({
    rideId: watchedRideId,
    enabled: !!watchedRideId,
    onMessage: onRideStatusMessage,
  });

  const confirmCancelBooking = useCallback(async () => {
    if (bookingToCancel == null) return;
    setCancelling(true);
    setError('');
    try {
      await cancelPassengerBooking(bookingToCancel);
      setPassengerList((prev) =>
        prev.map((item) =>
          item.bookingId === bookingToCancel ? { ...item, bookingStatus: 'cancelled' } : item
        )
      );
      setBookingToCancel(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, apiErr('err_cancel_booking')));
      await fetchPassengerBookings();
    } finally {
      setCancelling(false);
    }
  }, [bookingToCancel, fetchPassengerBookings, setError]);

  return {
    passengerList,
    passengerLoading,
    bookingToCancel,
    setBookingToCancel,
    cancelling,
    confirmCancelBooking,
  };
}
