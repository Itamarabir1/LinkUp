import { useState } from 'react';
import { WS_URLS } from '../config/wsUrls';
import { PassengerLocationEventSchema } from '../types/wsEvents';
import { useReconnectingWebSocketState } from './useReconnectingWebSocketState';

export interface PassengerLocationUpdate {
  booking_id: string;
  passenger_id: string;
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
  timestamp: string;
}

/**
 * נהג מאזין לעדכוני מיקום נוסעים בנסיעה (ערוץ ride_{ride_id}:passenger_locations).
 */
export function usePassengerLocations(rideId: string | null) {
  const [locations, setLocations] = useState<PassengerLocationUpdate[]>([]);

  const { connected, error } = useReconnectingWebSocketState({
    buildUrl: (token) => WS_URLS.ridePassengers(rideId!, token),
    enabled: !!rideId,
    reconnectKey: rideId,
    connectionErrorLabel: 'שגיאת חיבור לעדכוני נוסעים',
    onMessage: (ev) => {
      try {
        const result = PassengerLocationEventSchema.safeParse(JSON.parse(ev.data as string));
        if (!result.success) {
          console.warn('[usePassengerLocations] unexpected payload:', ev.data);
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
    },
    onReset: () => setLocations([]),
  });

  return { locations, error, connected };
}
