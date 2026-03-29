import { useEffect, useState } from 'react';
import { getWsBaseUrl } from '../config/env';
import { PassengerLocationEventSchema } from '../types/wsEvents';

export interface PassengerLocationUpdate {
  booking_id: string;
  passenger_id: string;
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
  timestamp: string;
}

function getPassengersWsUrl(rideId: string): string {
  const token = localStorage.getItem('linkup_access_token');
  const path = `${getWsBaseUrl()}/rides/ws/${rideId}/passengers`;
  return token ? `${path}?token=${encodeURIComponent(token)}` : path;
}

/**
 * נהג מאזין לעדכוני מיקום נוסעים בנסיעה (ערוץ ride_{ride_id}:passenger_locations).
 */
export function usePassengerLocations(rideId: string | null) {
  const [locations, setLocations] = useState<PassengerLocationUpdate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!rideId) {
      queueMicrotask(() => {
        setLocations([]);
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
      ws = new WebSocket(getPassengersWsUrl(rideId));

      ws.onopen = () => {
        setError(null);
        setConnected(true);
      };
      ws.onclose = () => {
        setConnected(false);
        ws = null;
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => setError('שגיאת חיבור לעדכוני נוסעים');

      ws.onmessage = (ev) => {
        try {
          const raw = JSON.parse(ev.data as string);
          const result = PassengerLocationEventSchema.safeParse(raw);
          if (!result.success) {
            console.warn('[usePassengerLocations] unexpected payload:', raw);
            return;
          }
          const update = result.data;
          setLocations((prev) => [
            ...prev.filter((p) => p.booking_id !== update.booking_id),
            {
              booking_id: update.booking_id,
              passenger_id: update.passenger_id,
              lat: update.lat,
              lng: update.lng,
              heading: update.heading,
              speed: update.speed,
              timestamp: update.timestamp ?? new Date().toISOString(),
            },
          ]);
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
      setLocations([]);
    };
  }, [rideId]);

  return { locations, error, connected };
}
