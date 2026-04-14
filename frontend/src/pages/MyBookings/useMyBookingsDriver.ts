import { useCallback, useEffect, useMemo, useState } from 'react';
import { useUserEvent } from '../../hooks/useUserEvent';
import { approveBooking, fetchDriverBookingSummary, rejectBooking } from '../../api/bookings';
import type { Ride } from '../../types/api';
import { cancelRide, endRide, startRide } from '../../api/rides';
import { useLocationBroadcast } from '../../hooks/useLocationBroadcast';
import { getApiErrorCode, getApiErrorMessage, getApiStatus } from '../../utils/apiError';
import type { DriverBookingItem, TabKind } from './myBookings.types';

type DriverStatus =
  | { kind: 'idle' }
  | { kind: 'loading'; busyBookingId?: string }
  | { kind: 'action'; bookingId: string };

/** טעינה, אישורים ושיתוף מיקום במצב נהג */
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
      const { data } = await fetchDriverBookingSummary();
      const rows = data?.rides ?? [];
      const items: DriverBookingItem[] = [];
      for (const row of rows) {
        const mappedPassengers = (row.passengers ?? []).map((p) => ({
          bookingId: p.booking_id,
          passengerName: p.passenger_name ?? 'נוסע',
          numSeats: p.num_seats,
          status: p.status,
          pickupName: p.pickup_name ?? null,
          pickupTime: p.pickup_time ?? null,
          dropoffName: p.destination_name ?? null,
        }));
        if (mappedPassengers.length === 0) continue;
        const ride: Ride = {
          ride_id: row.ride_id,
          driver_id: userId,
          group_id: row.group_id ?? null,
          group_name: row.group_name ?? null,
          origin_name: row.origin_name,
          destination_name: row.destination_name,
          departure_time: row.departure_time,
          estimated_arrival_time: row.estimated_arrival_time,
          available_seats: row.available_seats,
          price: row.price,
          status: row.status,
          created_at: row.departure_time,
        };
        items.push({ ride, passengers: mappedPassengers });
      }
      setDriverList(items);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינת ההזמנות נכשלה'));
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
        setError(detail || 'התחלת הנסיעה נכשלה');
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
        setError(getApiErrorMessage(err, 'אישור הבקשה נכשל'));
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
        setError(getApiErrorMessage(err, 'דחיית הבקשה נכשלה'));
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
      setError(getApiErrorMessage(err, 'ביטול הנסיעה נכשל'));
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
