import * as Sentry from '@sentry/react';
import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { STORAGE_KEYS } from '../config/constants';
import { API_BASE_URL, API_TIMEOUT_MS } from '../config/env';

// Log resolved API base (browser devtools console)
console.log('[LinkUp Frontend] API Base URL:', API_BASE_URL);

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

function getStoredAccessToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
}

function getStoredRefreshToken(): string | null {
  return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, access);
  localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) return null;
  try {
    const { data } = await axios.post<{
      access_token: string;
      refresh_token: string;
    }>(`${API_BASE_URL}/auth/refresh`, { refresh_token: refresh }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: API_TIMEOUT_MS,
    });
    const newAccess = data.access_token;
    const newRefresh = data.refresh_token;
    if (newAccess) {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, newAccess);
      if (newRefresh) localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, newRefresh);
      return newAccess;
    }
  } catch {
    clearTokens();
  }
  return null;
}

let isRefreshing = false;
const failedQueue: Array<{
  resolve: (token: string | null) => void;
  reject: (err: AxiosError) => void;
}> = [];

function processQueue(error: AxiosError | null, token: string | null) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  failedQueue.length = 0;
}

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getStoredAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (err) => Promise.reject(err)
);

api.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };
    if (err.response?.status !== 401 || original._retry) {
      return Promise.reject(err);
    }
    if (isRefreshing) {
      return new Promise<void>((resolve, reject) => {
        failedQueue.push({
          resolve: (t) => {
            if (t) original.headers.Authorization = `Bearer ${t}`;
            resolve();
          },
          reject,
        });
      }).then(() => api(original));
    }
    original._retry = true;
    isRefreshing = true;
    const newToken = await refreshAccessToken();
    isRefreshing = false;
    processQueue(null, newToken);
    if (newToken) {
      original.headers.Authorization = `Bearer ${newToken}`;
      return api(original);
    }
    processQueue(err, null);
    return Promise.reject(err);
  }
);

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status !== 401) {
      console.error('[LinkUp] API Error:', {
        error_code: (err.response?.data as { error_code?: string } | undefined)?.error_code,
        message: (err.response?.data as { message?: string } | undefined)?.message,
        trace_id: (err.response?.data as { trace_id?: string } | undefined)?.trace_id,
        status: err.response?.status,
      });
      if (
        import.meta.env.PROD &&
        axios.isAxiosError(err) &&
        err.code !== 'ERR_CANCELED' &&
        err.response?.status &&
        err.response.status >= 500
      ) {
        (err as { __sentryCaptured?: boolean }).__sentryCaptured = true;
        Sentry.captureException(err);
      }
    }
    return Promise.reject(err);
  }
);

/** HTTP client for chat-ws presence endpoints (not backend API). */
export const chatWsApi = axios.create({
  baseURL: '',
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});
chatWsApi.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
