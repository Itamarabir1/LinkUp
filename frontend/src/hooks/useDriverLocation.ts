import { useState } from 'react';
import { WS_URLS } from '../config/wsUrls';
import { DriverLocationEventSchema } from '../types/wsEvents';
import { useReconnectingWebSocketState } from './useReconnectingWebSocketState';

export interface DriverLocationUpdate {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
  timestamp: string;
  ride_id?: string;
}

/**
 */
export function useDriverLocation(bookingId: string | null) {
  const [position, setPosition] = useState<DriverLocationUpdate | null>(null);

  const { connected, error } = useReconnectingWebSocketState({
    buildUrl: (token) => WS_URLS.bookingLocation(bookingId!, token),
    enabled: !!bookingId,
    reconnectKey: bookingId,
    connectionErrorLabel: 'שגיאת חיבור לעדכון מיקום הנהג',
    onMessage: (ev) => {
      try {
        const result = DriverLocationEventSchema.safeParse(JSON.parse(ev.data as string));
        if (!result.success) {
          console.warn('[useDriverLocation] unexpected payload:', ev.data);
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
    },
    onReset: () => setPosition(null),
  });

  return { position, error, connected };
}
