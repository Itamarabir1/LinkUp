import { useCallback, useState } from 'react';
import { useInfiniteQuery, useMutation, useQueryClient, type InfiniteData } from '@tanstack/react-query';
import { cancelPassengerRequest, fetchMyPassengerRequests } from '../api/passengers';
import { mk, qk } from '../api/queryKeys';
import type { PaginatedPassengerRequestsResponse, PassengerRequest } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { useUserEvent } from '../hooks/useUserEvent';

export function useMyRequests() {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');
  const [requestToCancel, setRequestToCancel] = useState<PassengerRequest | null>(null);
  const { data, isLoading } = useInfiniteQuery({
    queryKey: qk.passengers.requests(),
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const { data: page } = await fetchMyPassengerRequests({ cursor: pageParam, limit: 100 });
      return page ?? { items: [], next_cursor: null, has_more: false };
    },
    getNextPageParam: (page) => page.next_cursor ?? undefined,
    staleTime: 30_000,
  });
  const requests = data?.pages.flatMap((p) => p.items) ?? [];

  const { mutate: mutateCancel, isPending: cancelling } = useMutation({
    mutationKey: mk.rides.cancel('request'),
    mutationFn: (requestId: string) => cancelPassengerRequest(requestId),
    onSuccess: (_, requestId) => {
      queryClient.setQueryData(
        qk.passengers.requests(),
        (old: InfiniteData<PaginatedPassengerRequestsResponse> | undefined) =>
          old
            ? {
                ...old,
                pages: old.pages.map((page) => ({
                  ...page,
                  items: page.items.map((r) =>
                    r.request_id === requestId ? { ...r, status: 'cancelled' as const } : r
                  ),
                })),
                pageParams: old.pageParams,
              }
            : old
      );
      setRequestToCancel(null);
    },
    onError: (err) => {
      setError(getApiErrorMessage(err, apiErr('err_cancel_request')));
    },
  });

  useUserEvent(
    'REQUEST_EXPIRED',
    useCallback((detail) => {
      if (!detail.request_id) return;
      queryClient.setQueryData(
        qk.passengers.requests(),
        (old: InfiniteData<PaginatedPassengerRequestsResponse> | undefined) =>
          old
            ? {
                ...old,
                pages: old.pages.map((page) => ({
                  ...page,
                  items: page.items.map((r) =>
                    r.request_id === detail.request_id
                      ? { ...r, status: 'expired' as const }
                      : r
                  ),
                })),
                pageParams: old.pageParams,
              }
            : old
      );
    }, [queryClient])
  );

  const confirmCancelRequest = useCallback(async () => {
    if (!requestToCancel) return;
    setError('');
    mutateCancel(requestToCancel.request_id);
  }, [requestToCancel, mutateCancel]);

  return {
    requests,
    loading: isLoading,
    error,
    requestToCancel,
    setRequestToCancel,
    cancelling,
    confirmCancelRequest,
  };
}
