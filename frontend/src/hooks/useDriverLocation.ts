import { useEffect, useState } from 'react';
import { getWsBaseUrl } from '../config/env';

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

    const url = getBookingLocationWsUrl(bookingId);
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setError(null);
      setConnected(true);
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError('שגיאת חיבור לעדכון מיקום הנהג');

    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data as string) as {
          type?: string;
          lat?: number;
          lng?: number;
          heading?: number;
          speed?: number;
          timestamp?: string;
          ride_id?: string;
        };
        if (payload.lat == null || payload.lng == null) return;
        setPosition({
          lat: payload.lat,
          lng: payload.lng,
          heading: payload.heading,
          speed: payload.speed,
          timestamp: payload.timestamp ?? new Date().toISOString(),
          ride_id: payload.ride_id,
        });
      } catch {
        // ignore invalid JSON
      }
    };

    return () => {
      ws.close();
      setPosition(null);
    };
  }, [bookingId]);

  return { position, error, connected };
}
