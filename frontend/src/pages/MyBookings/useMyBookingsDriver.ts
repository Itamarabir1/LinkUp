import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  approveBooking,
  fetchRideManifest,
  rejectBooking,
} from '../../api/bookings';
import { cancelRide, endRide, fetchMyRides, startRide } from '../../api/rides';
import { useLocationBroadcast } from '../../hooks/useLocationBroadcast';
import { getApiErrorCode, getApiErrorMessage, getApiStatus } from '../../utils/apiError';
import type { DriverBookingItem, TabKind } from './myBookings.types';

/** טעינה, אישורים ושיתוף מיקום במצב נהג */
export function useMyBookingsDriver(
  user: { user_id: string } | null | undefined,
  activeTab: TabKind,
  setError: (message: string) => void
) {
  const userId = user?.user_id;
  const [driverList, setDriverList] = useState<DriverBookingItem[]>([]);
  const [driverLoading, setDriverLoading] = useState(false);
  const [sharingRideId, setSharingRideId] = useState<string | null>(null);
  const [liveRideId, setLiveRideId] = useState<string | null>(null);
  const [rideToCancel, setRideToCancel] = useState<string | null>(null);
  const [cancellingRide, setCancellingRide] = useState(false);
  const [actionBookingId, setActionBookingId] = useState<string | null>(null);

  const fetchDriverBookings = useCallback(async () => {
    if (!userId) return;
    setDriverLoading(true);
    setError('');
    try {
      const { data: myRides } = await fetchMyRides();
      const activeRides = (Array.isArray(myRides) ? myRides : []).filter((r) => r.status !== 'cancelled');
      const items: DriverBookingItem[] = [];
      await Promise.all(
        activeRides.map(async (ride) => {
          try {
            const manifestRes = await fetchRideManifest(ride.ride_id, userId);
            const passengers = manifestRes.data?.passengers ?? [];
            const filteredPassengers = passengers
              .filter((p) => p.status === 'pending_approval' || p.status === 'confirmed')
              .map((p) => ({
                bookingId: p.booking_id,
                passengerName: p.passenger_name ?? 'נוסע',
                numSeats: p.num_seats,
                status: p.status,
                pickupName: p.pickup_name ?? null,
                pickupTime: p.pickup_time ?? null,
                dropoffName: p.destination_name ?? null,
              }));

            if (filteredPassengers.length > 0) {
              items.push({ ride, passengers: filteredPassengers });
            }
          } catch {
            // skip ride
          }
        })
      );
      items.sort(
        (a, b) =>
          new Date(a.ride.departure_time).getTime() - new Date(b.ride.departure_time).getTime()
      );
      setDriverList(items);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינת ההזמנות נכשלה'));
    } finally {
      setDriverLoading(false);
    }
  }, [userId, setError]);

  useEffect(() => {
    if (activeTab === 'driver') void fetchDriverBookings();
  }, [activeTab, fetchDriverBookings]);

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
      setActionBookingId(bookingId);
      setError('');
      try {
        await approveBooking(bookingId, userId);
        await fetchDriverBookings();
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, 'אישור הבקשה נכשל'));
      } finally {
        setActionBookingId(null);
      }
    },
    [userId, fetchDriverBookings, setError]
  );

  const handleReject = useCallback(
    async (bookingId: string) => {
      if (!userId) return;
      setActionBookingId(bookingId);
      setError('');
      try {
        await rejectBooking(bookingId, userId);
        await fetchDriverBookings();
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, 'דחיית הבקשה נכשלה'));
      } finally {
        setActionBookingId(null);
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
      if (sharingRideId === rideToCancel) setSharingRideId(null);
      setLiveRideId((prev) => (prev === rideToCancel ? null : prev));
      setRideToCancel(null);
      await fetchDriverBookings();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'ביטול הנסיעה נכשל'));
    } finally {
      setCancellingRide(false);
    }
  }, [rideToCancel, sharingRideId, fetchDriverBookings, setError]);

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
    actionBookingId,
    handleShareStart,
    handleShareStop,
    handleApprove,
    handleReject,
    confirmCancelRide,
  };
}
