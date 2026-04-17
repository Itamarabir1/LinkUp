import { getChatWebSocketUrl, getWsBaseUrl } from './env';
import { STORAGE_KEYS } from './constants';

/**
 * Single source of truth for all WebSocket URLs.
 * If API paths change, update this file only.
 */
export function getWsToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

export const WS_URLS = {
  ride: (rideId: string, token: string) =>
    `${getWsBaseUrl()}/rides/ws/${rideId}?token=${encodeURIComponent(token)}`,

  ridePassengers: (rideId: string, token: string) =>
    `${getWsBaseUrl()}/rides/ws/${rideId}/passengers?token=${encodeURIComponent(token)}`,

  bookingLocation: (bookingId: string, token: string) =>
    `${getWsBaseUrl()}/bookings/ws/${bookingId}/location?token=${encodeURIComponent(token)}`,

  chat: (token: string) => getChatWebSocketUrl(token),
} as const;
