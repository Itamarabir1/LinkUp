import { useEffect, useState } from 'react';
import { getWsBaseUrl } from '../config/env';

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

    const url = getPassengersWsUrl(rideId);
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setError(null);
      setConnected(true);
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setError('שגיאת חיבור לעדכוני נוסעים');

    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data as string) as {
          type?: string;
          booking_id?: string;
          passenger_id?: string;
          lat?: number;
          lng?: number;
          heading?: number;
          speed?: number;
          timestamp?: string;
        };
        if (payload.type !== 'passenger_location' || payload.lat == null || payload.lng == null) return;
        const update: PassengerLocationUpdate = {
          booking_id: payload.booking_id ?? '',
          passenger_id: payload.passenger_id ?? '',
          lat: payload.lat,
          lng: payload.lng,
          heading: payload.heading,
          speed: payload.speed,
          timestamp: payload.timestamp ?? new Date().toISOString(),
        };
        setLocations((prev) => {
          const rest = prev.filter((p) => p.booking_id !== update.booking_id);
          return [...rest, update];
        });
      } catch {
        // ignore invalid JSON
      }
    };

    return () => {
      ws.close();
      setLocations([]);
    };
  }, [rideId]);

  return { locations, error, connected };
}
