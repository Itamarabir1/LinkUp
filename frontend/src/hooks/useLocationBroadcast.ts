import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchRideManifest, postDriverBookingLocation, type RideManifestPassenger } from '../api/bookings';
import { getApiErrorMessage, getApiStatus } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { useLocationWatcher } from './useLocationWatcher';

export interface DriverPosition {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
  timestamp: string;
}

export interface UseLocationBroadcastOptions {
  rideId: string | null;
  driverId: string | null;
  enabled: boolean;
  /** Optional booking id used for POST /location without manifest lookup. */
  bookingId?: string | null;
  onPosition?: (pos: DriverPosition) => void;
  onStart?: (rideId: string) => void | Promise<void>;
  onStop?: (rideId: string) => void | Promise<void>;
}

/**
 * הנהג שולח מיקום לשרת; אופציונלי: onStart אחרי שליחה ראשונה מוצלחת, onStop כשמשביתים שיתוף.
 */
export function useLocationBroadcast(options: UseLocationBroadcastOptions) {
  const { rideId, driverId, enabled, bookingId: bookingIdProp, onPosition, onStart, onStop } = options;
  const [error, setError] = useState<string | null>(null);
  const [fetchedBookingId, setFetchedBookingId] = useState<string | null>(null);
  const directBookingId =
    bookingIdProp != null && String(bookingIdProp).length > 0 ? String(bookingIdProp) : null;
  const bookingId = directBookingId ?? fetchedBookingId;
  const hasStartedRef = useRef(false);
  const activeRideIdRef = useRef<string | null>(null);
  const wasEnabledRef = useRef(false);
  const prevRideIdRef = useRef<string | null>(null);

  const onPositionRef = useRef(onPosition);
  const onStartRef = useRef(onStart);
  const onStopRef = useRef(onStop);
  useEffect(() => {
    onPositionRef.current = onPosition;
    onStartRef.current = onStart;
    onStopRef.current = onStop;
  });

  const fetchOneBookingId = useCallback(async (rId: string): Promise<string | null> => {
    try {
      const { data } = await fetchRideManifest(rId);
      const confirmed = (data?.passengers ?? []).find((p: RideManifestPassenger) => p.status === 'confirmed');
      return confirmed?.booking_id ?? data?.passengers?.[0]?.booking_id ?? null;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (enabled && rideId) activeRideIdRef.current = rideId;
  }, [enabled, rideId]);

  useEffect(() => {
    const prev = prevRideIdRef.current;
    if (
      enabled &&
      prev &&
      rideId &&
      prev !== rideId &&
      hasStartedRef.current &&
      onStopRef.current
    ) {
      hasStartedRef.current = false;
      void Promise.resolve(onStopRef.current(prev)).catch(() => {});
    }
    if (rideId) prevRideIdRef.current = rideId;
    else if (!enabled) prevRideIdRef.current = null;
  }, [enabled, rideId]);

  useEffect(() => {
    if (wasEnabledRef.current && !enabled) {
      const rid = activeRideIdRef.current;
      if (hasStartedRef.current && onStopRef.current && rid) {
        hasStartedRef.current = false;
        void Promise.resolve(onStopRef.current(rid)).catch(() => {});
      }
      activeRideIdRef.current = null;
    }
    wasEnabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !rideId || !driverId) {
      queueMicrotask(() => setFetchedBookingId(null));
      return;
    }
    if (directBookingId) {
      return;
    }
    let cancelled = false;
    fetchOneBookingId(rideId).then((id) => {
      if (!cancelled) setFetchedBookingId(id);
    });
    return () => {
      cancelled = true;
    };
  }, [enabled, rideId, driverId, directBookingId, fetchOneBookingId]);

  useEffect(() => {
    if (!enabled) return;
    if (!rideId || !bookingId) return;
    if (hasStartedRef.current) return;

    const startFn = onStartRef.current;
    if (!startFn) return;

    void (async () => {
      try {
        await startFn(rideId);
        hasStartedRef.current = true;
      } catch (error: unknown) {
        const status = getApiStatus(error);
        // 400 = ride already active or status disallows start — do not block location streaming
        if (status === 400) {
          hasStartedRef.current = true;
        }
      }
    })();
  }, [enabled, rideId, bookingId]);

  useLocationWatcher({
    enabled: enabled && !!rideId && !!bookingId,
    onPosition: ({ lat, lng, heading, speed }) => {
      if (!bookingId) return;
      const payload = { lat, lng, heading, speed };
      postDriverBookingLocation(bookingId, payload)
        .then(() => {
          setError(null);
          const ts = new Date().toISOString();
          onPositionRef.current?.({ lat, lng, heading, speed, timestamp: ts });
        })
        .catch((err: unknown) => {
          setError(getApiErrorMessage(err, apiErr('err_send_location')));
        });
    },
    onError: (msg) => setError(msg),
    throttleMs: 1500,
  });

  return { error, bookingId, isActive: enabled && !!bookingId };
}
