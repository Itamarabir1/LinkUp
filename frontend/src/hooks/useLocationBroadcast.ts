import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
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
  /** אם מועבר — משמש ל־POST /location בלי לטעון מ-manifest */
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

  const fetchOneBookingId = useCallback(async (rId: string, dId: string): Promise<string | null> => {
    try {
      const { data } = await api.get<{ passengers: Array<{ booking_id: string; status: string }> }>(
        `/bookings/ride/${rId}/manifest`,
        { params: { driver_id: dId } }
      );
      const confirmed = (data?.passengers ?? []).find((p) => p.status === 'confirmed');
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
    fetchOneBookingId(rideId, driverId).then((id) => {
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
        const status = (error as { response?: { status?: number } })?.response?.status;
        // 400 = נסיעה כבר active (או סטטוס לא מאפשר start) — לא חוסם שידור מיקום
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
      api
        .post(`/bookings/${bookingId}/location`, payload, { timeout: 5000 })
        .then(() => {
          setError(null);
          const ts = new Date().toISOString();
          onPositionRef.current?.({ lat, lng, heading, speed, timestamp: ts });
        })
        .catch((err) => {
          const msg = err?.response?.data?.detail ?? 'שליחת מיקום נכשלה';
          setError(typeof msg === 'string' ? msg : String(msg));
        });
    },
    onError: (msg) => setError(msg),
    throttleMs: 3000,
  });

  return { error, bookingId, isActive: enabled && !!bookingId };
}
