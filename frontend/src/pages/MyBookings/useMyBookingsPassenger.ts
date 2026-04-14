import { useCallback, useEffect, useState } from 'react';
import { useUserEvent } from '../../hooks/useUserEvent';
import { cancelPassengerBooking, fetchPassengerBookingSummary } from '../../api/bookings';
import { getApiErrorMessage } from '../../utils/apiError';
import type { Ride } from '../../types/api';
import { useRideWebSocket } from '../../hooks/useRideWebSocket';
import type { RideEvent } from '../../types/wsEvents';
import type { PassengerBookingItem } from './myBookings.types';
import { LIVE_STATUSES } from '../../constants/rideStatuses';

/** טעינה וביטול הזמנות במצב נוסע */
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
      const { data } = await fetchPassengerBookingSummary();
      const rows = data?.bookings ?? [];
      const items: PassengerBookingItem[] = rows.map((row) => {
        const ride: Ride = {
          ride_id: row.ride_id,
          driver_id: '',
          group_id: row.group_id ?? null,
          group_name: row.group_name ?? null,
          origin_name: row.origin_name,
          destination_name: row.destination_name,
          departure_time: row.departure_time,
          estimated_arrival_time: row.estimated_arrival_time,
          available_seats: 0,
          price: 0,
          status: row.ride_status,
          created_at: row.departure_time,
        };
        return {
          ride,
          bookingId: row.booking_id,
          bookingStatus: row.booking_status,
          driverName: row.driver?.full_name ?? null,
        };
      });
      setPassengerList(items);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינת ההזמנות נכשלה'));
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
      setError(getApiErrorMessage(err, 'ביטול ההזמנה נכשל'));
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
