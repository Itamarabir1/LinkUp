import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL, API_TIMEOUT_MS } from '../config/env';

// לוודא לאן הבקשות הולכות (יופיע בקונסול של הדפדפן F12)
console.log('[Linkup Frontend] API Base URL:', API_BASE_URL);

const TOKEN_KEY = 'linkup_access_token';
const REFRESH_KEY = 'linkup_refresh_token';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
});

function getStoredAccessToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
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
      localStorage.setItem(TOKEN_KEY, newAccess);
      if (newRefresh) localStorage.setItem(REFRESH_KEY, newRefresh);
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
      console.error('[Linkup] API Error:', {
        error_code: (err.response?.data as { error_code?: string } | undefined)?.error_code,
        message: (err.response?.data as { message?: string } | undefined)?.message,
        trace_id: (err.response?.data as { trace_id?: string } | undefined)?.trace_id,
        status: err.response?.status,
      });
      // TODO: Sentry — להסיר הערה כשעוברים לפרודקשן
      // רק 5xx — לא לשלוח 4xx עסקיים (מפחית רעש)
      // import * as Sentry from "@sentry/react";
      // if (import.meta.env.PROD && err.response?.status && err.response.status >= 500) {
      //   Sentry.captureException(err);
      // }
    }
    return Promise.reject(err);
  }
);

/** בקשות HTTP ל-chat-ws (presence) — לא ל-backend */
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
