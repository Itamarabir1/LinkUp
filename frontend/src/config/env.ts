export const API_BASE_URL = '/api/v1';
export const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
export const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 30000;

export function getChatWebSocketUrl(token: string): string {
  if (import.meta.env.DEV) {
    return `ws://localhost:8081/ws?token=${encodeURIComponent(token)}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;
}

export function getWsBaseUrl(): string {
  if (import.meta.env.DEV) {
    return 'ws://localhost:8000/api/v1';
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/api/v1`;
}

export function getRideWebSocketUrl(rideId: string, token: string): string {
  const base = getWsBaseUrl();
  return `${base}/rides/ws/${rideId}?token=${encodeURIComponent(token)}`;
}
