import { useCallback, useEffect, useState } from 'react';
import { cancelPassengerBooking, fetchMyBookings } from '../../api/bookings';
import { fetchPassengerDriverInfo, fetchRideById } from '../../api/rides';
import { getApiErrorMessage } from '../../utils/apiError';
import type { BookingRow, PassengerBookingItem } from './myBookings.types';

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
      const { data } = await fetchMyBookings(userId, 50);
      const bookings = Array.isArray(data) ? data : [];
      const asPassenger = bookings.filter(
        (b) =>
          b.passenger_id === userId &&
          (b.status === 'pending_approval' || b.status === 'confirmed')
      );
      const byRideId = new Map<string, BookingRow>();
      asPassenger.forEach((b) => {
        if (!byRideId.has(b.ride_id)) byRideId.set(b.ride_id, b);
      });
      const rideIds = Array.from(byRideId.keys());
      const items: PassengerBookingItem[] = [];
      await Promise.all(
        rideIds.map(async (rideId) => {
          try {
            const [rideRes, driverRes] = await Promise.all([
              fetchRideById(rideId),
              fetchPassengerDriverInfo(rideId).catch(() => null),
            ]);
            const ride = rideRes.data;
            if (ride.status === 'cancelled') return;
            const booking = byRideId.get(rideId)!;
            items.push({
              ride,
              bookingId: booking.booking_id,
              bookingStatus: booking.status,
              driverName: driverRes?.data?.full_name ?? null,
            });
          } catch {
            // skip ride
          }
        })
      );
      items.sort(
        (a, b) =>
          new Date(a.ride.departure_time).getTime() - new Date(b.ride.departure_time).getTime()
      );
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

  const confirmCancelBooking = useCallback(async () => {
    if (bookingToCancel == null) return;
    setCancelling(true);
    setError('');
    try {
      await cancelPassengerBooking(bookingToCancel);
      setBookingToCancel(null);
      await fetchPassengerBookings();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'ביטול ההזמנה נכשל'));
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
