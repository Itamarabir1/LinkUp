import axios from 'axios';
import { STORAGE_KEYS } from '../config/constants';
import { API_BASE_URL, API_TIMEOUT_MS } from '../config/env';
import { isTokenExpiredOrNearExpiry } from '../utils/tokenUtils';

/* ── token storage helpers (shared with client.ts) ────────────── */

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

export function setTokens(access: string): void {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, access);
}

export function clearTokens(): void {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem('linkup_refresh_token');
}

/* ── session-expired event (single-flight) ────────────────────── */

let sessionExpiredEmitted = false;
export function emitSessionExpired(): void {
  if (typeof window === 'undefined') return;
  if (sessionExpiredEmitted) return;
  sessionExpiredEmitted = true;
  queueMicrotask(() => {
    window.dispatchEvent(new Event('auth:session-expired'));
    queueMicrotask(() => {
      sessionExpiredEmitted = false;
    });
  });
}

/* ── refresh access token via HttpOnly cookie ─────────────────── */

async function refreshAccessToken(): Promise<string | null> {
  try {
    const { data } = await axios.post<{
      access_token: string;
    }>(`${API_BASE_URL}/auth/refresh`, {}, {
      headers: { 'Content-Type': 'application/json' },
      timeout: API_TIMEOUT_MS,
      withCredentials: true,
    });
    const newAccess = data.access_token;
    if (newAccess) {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, newAccess);
      return newAccess;
    }
  } catch {
    clearTokens();
    emitSessionExpired();
  }
  return null;
}

/* ── coordinated refresh (deduplicates concurrent callers) ────── */

let isRefreshing = false;
const waiters: Array<{
  resolve: (token: string | null) => void;
  reject: (err: unknown) => void;
}> = [];

function drainWaiters(error: unknown | null, token: string | null) {
  waiters.forEach((w) => (error ? w.reject(error) : w.resolve(token)));
  waiters.length = 0;
}

/**
 * Coordinate a single in-flight refresh across callers (Axios interceptor
 * **and** WebSocket reconnect hooks).
 *
 * Returns the new access token string, or `null` when the session is dead
 * (refresh cookie expired / revoked).
 */
export async function coordinatedRefresh(): Promise<string | null> {
  if (isRefreshing) {
    return new Promise<string | null>((resolve, reject) => {
      waiters.push({ resolve, reject });
    });
  }
  isRefreshing = true;
  try {
    const token = await refreshAccessToken();
    drainWaiters(null, token);
    return token;
  } catch (err) {
    drainWaiters(err, null);
    return null;
  } finally {
    isRefreshing = false;
  }
}

/**
 * Return a **valid** access token for use in WebSocket `?token=` params.
 *
 * 1. Reads the current token from localStorage.
 * 2. If the token is missing → return `null` (not logged in).
 * 3. If the token is expired or near-expiry (< 60 s) → refresh first.
 * 4. If refresh fails → emit `auth:session-expired`, return `null`.
 */
export async function ensureFreshToken(): Promise<string | null> {
  const current = getStoredAccessToken();
  if (!current) return null;
  if (!isTokenExpiredOrNearExpiry(current)) return current;

  const refreshed = await coordinatedRefresh();
  return refreshed;
}
