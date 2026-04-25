import { APP_CONFIG } from './runtime';

export const API_BASE_URL = '/api/v1';
export const GOOGLE_MAPS_API_KEY = APP_CONFIG.googleMaps.apiKey;
export const API_TIMEOUT_MS = APP_CONFIG.api.timeoutMs;

export function getChatWebSocketUrl(token: string): string {
  if (import.meta.env.DEV) {
    return `ws://127.0.0.1:8081/ws?token=${encodeURIComponent(token)}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;
}

export function getWsBaseUrl(): string {
  if (import.meta.env.DEV) {
    return 'ws://127.0.0.1:8000/api/v1';
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/api/v1`;
}
