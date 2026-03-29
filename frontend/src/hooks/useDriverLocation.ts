import { useEffect, useState } from 'react';
import { getWsBaseUrl } from '../config/env';
import { DriverLocationEventSchema } from '../types/wsEvents';

export interface DriverLocationUpdate {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
  timestamp: string;
  ride_id?: string;
}

function getBookingLocationWsUrl(bookingId: string): string {
  const token = localStorage.getItem('linkup_access_token');
  const path = `${getWsBaseUrl()}/bookings/ws/${bookingId}/location`;
  return token ? `${path}?token=${encodeURIComponent(token)}` : path;
}

/**
 * נוסע מאזין למיקום הנהג – ערוץ booking_{booking_id}.
 */
export function useDriverLocation(bookingId: string | null) {
  const [position, setPosition] = useState<DriverLocationUpdate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!bookingId) {
      queueMicrotask(() => {
        setPosition(null);
        setError(null);
        setConnected(false);
      });
      return;
    }

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      ws = new WebSocket(getBookingLocationWsUrl(bookingId));

      ws.onopen = () => {
        setError(null);
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        ws = null;
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => setError('שגיאת חיבור לעדכון מיקום הנהג');

      ws.onmessage = (ev) => {
        try {
          const raw = JSON.parse(ev.data as string);
          const result = DriverLocationEventSchema.safeParse(raw);
          if (!result.success) {
            console.warn('[useDriverLocation] unexpected payload:', raw);
            return;
          }
          const payload = result.data;
          setPosition({
            lat: payload.lat,
            lng: payload.lng,
            heading: payload.heading,
            speed: payload.speed,
            timestamp: payload.timestamp ?? new Date().toISOString(),
            ride_id: payload.ride_id,
          });
        } catch {
          /* ignore */
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      ws?.close();
      setPosition(null);
    };
  }, [bookingId]);

  return { position, error, connected };
}
