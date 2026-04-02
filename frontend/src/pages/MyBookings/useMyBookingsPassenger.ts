import { useCallback, useEffect, useState } from 'react';
import { cancelPassengerBooking, fetchMyBookings } from '../../api/bookings';
import { fetchPassengerDriverInfo, fetchRideById } from '../../api/rides';
import { getApiErrorMessage } from '../../utils/apiError';
import { useRideWebSocket } from '../../hooks/useRideWebSocket';
import type { RideEvent } from '../../types/wsEvents';
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
      const { data } = await fetchMyBookings(50);
      const asPassenger = data.filter(
        (b) =>
          b.passenger_id === userId
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

  useEffect(() => {
    const onUserEvent = (evt: Event) => {
      const detail = (evt as CustomEvent<{ event?: string; booking_id?: string }>).detail;
      if (detail?.event !== 'BOOKING_COMPLETED' || !detail.booking_id) return;
      setPassengerList((prev) =>
        prev.map((item) =>
          item.bookingId === detail.booking_id ? { ...item, bookingStatus: 'completed' } : item
        )
      );
    };
    window.addEventListener('linkup:user-event', onUserEvent as EventListener);
    return () => window.removeEventListener('linkup:user-event', onUserEvent as EventListener);
  }, []);

  const watchedRideId =
    passengerList.find(
      (item) =>
        item.bookingStatus === 'confirmed' && item.ride.status !== 'active'
    )?.ride.ride_id ?? null;

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
