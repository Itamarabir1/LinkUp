import { useEffect, useState } from 'react';
import { api } from '../api/client';
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
      api
        .post(
          `/bookings/${bookingId}/passenger-location`,
          { lat, lng, heading, speed },
          { timeout: 5000 }
        )
        .then(() => setError(null))
        .catch((err) => {
          const msg = err?.response?.data?.detail ?? 'שליחת מיקום נכשלה';
          setError(typeof msg === 'string' ? msg : String(msg));
        });
    },
    onError: (msg) => setError(msg),
    throttleMs: 3000,
  });

  return { error, isActive: enabled && !!bookingId };
}
