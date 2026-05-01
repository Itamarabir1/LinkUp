import { QueryCache, QueryClient, MutationCache } from '@tanstack/react-query';
import * as Sentry from '@sentry/react';
import axios from 'axios';

const isAxiosCanceled = (err: unknown): boolean =>
  axios.isAxiosError(err) && (err.code === 'ERR_CANCELED' || err.message === 'canceled');

const isRetryable = (err: unknown): boolean => {
  if (isAxiosCanceled(err)) return false;
  if (!axios.isAxiosError(err)) return false;
  if (!err.response) return true;
  const s = err.response.status;
  if (s === 401 || s === 403) return false;
  if (s >= 400 && s < 500) return false;
  return true;
};

const parseRetryAfter = (err: unknown): number | null => {
  if (!axios.isAxiosError(err)) return null;
  const raw = err.response?.headers?.['retry-after'];
  if (!raw) return null;

  const seconds = Number(raw);
  if (Number.isFinite(seconds)) return Math.max(0, seconds * 1000);

  const dateMs = Date.parse(raw);
  if (!Number.isNaN(dateMs)) return Math.max(0, dateMs - Date.now());

  return null;
};

function shouldSkipSentryForApiError(err: unknown): boolean {
  if (!axios.isAxiosError(err)) return false;
  return err.response?.status === 401;
}

const captureExceptionOnce = (error: unknown) => {
  const e = error as { __sentryCaptured?: boolean };
  if (e.__sentryCaptured) return;
  if (isAxiosCanceled(error)) return;
  if (shouldSkipSentryForApiError(error)) return;
  if (import.meta.env.PROD) {
    e.__sentryCaptured = true;
    Sentry.captureException(error);
  }
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => isRetryable(error) && failureCount < 2,
      retryDelay: (attemptIndex, error) =>
        parseRetryAfter(error) ?? Math.min(1000 * 2 ** attemptIndex, 30_000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: false,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => captureExceptionOnce(error),
  }),
  mutationCache: new MutationCache({
    onError: (error) => captureExceptionOnce(error),
  }),
});
