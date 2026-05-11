import * as Sentry from '@sentry/react';
import axios, { type AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL, API_TIMEOUT_MS } from '../config/env';
import { throttle } from './throttle';
import {
  getStoredAccessToken,
  setTokens,
  clearTokens,
  coordinatedRefresh,
} from './tokenRefresh';

export { setTokens, clearTokens };

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

/**
 * Orval mutator wrapper around the shared Axios instance.
 * Returns response payload directly so generated clients stay typed and concise.
 */
export const apiMutator = <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig
): Promise<T> => {
  return api({
    ...config,
    ...options,
  }).then(({ data }) => data as T);
};

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      await throttle();
    } catch (err) {
      if (import.meta.env.PROD) {
        Sentry.addBreadcrumb({
          category: 'throttle',
          message: 'Request throttled',
          level: 'warning',
          data: { url: config.url },
        });
      }
      return Promise.reject(err);
    }
    return config;
  },
  (err) => Promise.reject(err)
);

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
    original._retry = true;
    const newToken = await coordinatedRefresh();
    if (newToken) {
      original.headers.Authorization = `Bearer ${newToken}`;
      return api(original);
    }
    if (err.response?.status === 401) {
      (err as { __sentryCaptured?: boolean }).__sentryCaptured = true;
    }
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
