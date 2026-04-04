import { getChatWebSocketUrl, getWsBaseUrl } from './env';
import { STORAGE_KEYS } from './constants';

/**
 * מקור אמת יחיד לכל WebSocket URLs.
 * שינוי נתיב API — שינוי כאן בלבד.
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

  notifications: (token: string) =>
    `${getWsBaseUrl()}/notifications/ws?token=${encodeURIComponent(token)}`,
} as const;
