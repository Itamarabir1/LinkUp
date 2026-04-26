import { WS_URLS } from '../config/wsUrls';
import { RideEventSchema, type RideEvent } from '../types/wsEvents';
import { useReconnectingWebSocket } from './useReconnectingWebSocket';

interface Options {
  rideId: string | null;
  onMessage: (msg: RideEvent) => void;
  enabled?: boolean;
}

/**
 */
export function useRideWebSocket({ rideId, onMessage, enabled = true }: Options) {
  useReconnectingWebSocket({
    buildUrl: (token) => WS_URLS.ride(rideId!, token),
    enabled: enabled && !!rideId,
    reconnectKey: rideId,
    onMessage: (ev) => {
      try {
        const result = RideEventSchema.safeParse(JSON.parse(ev.data as string));
        if (!result.success) {
          console.warn('[useRideWebSocket] unexpected payload:', result.error.flatten());
          return;
        }
        onMessage(result.data);
      } catch {
        /* ignore malformed JSON */
      }
    },
  });
}
