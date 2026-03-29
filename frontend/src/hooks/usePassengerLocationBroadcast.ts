import { useEffect, useState } from 'react';
import { postPassengerBookingLocation } from '../api/bookings';
import { getApiErrorMessage } from '../utils/apiError';
import { useLocationWatcher } from './useLocationWatcher';

/**
 * נוסע שולח מיקום לנהג – POST /bookings/{booking_id}/passenger-location.
 * מופעל רק כאשר enabled=true (למשל לחיצה על "שתף מיקום").
 */
export function usePassengerLocationBroadcast(bookingId: string | null, enabled: boolean) {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !bookingId) {
      queueMicrotask(() => setError(null));
      return;
    }
  }, [enabled, bookingId]);

  useLocationWatcher({
    enabled: enabled && !!bookingId,
    onPosition: ({ lat, lng, heading, speed }) => {
      if (!bookingId) return;
      postPassengerBookingLocation(bookingId, { lat, lng, heading, speed })
        .then(() => setError(null))
        .catch((err: unknown) => {
          setError(getApiErrorMessage(err, 'שליחת מיקום נכשלה'));
        });
    },
    onError: (msg) => setError(msg),
    throttleMs: 1500,
  });

  return { error, isActive: enabled && !!bookingId };
}
