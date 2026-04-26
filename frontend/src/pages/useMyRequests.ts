import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { cancelPassengerRequest, fetchMyPassengerRequests } from '../api/passengers';
import { mk, qk } from '../api/queryKeys';
import type { PassengerRequest } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import { useUserEvent } from '../hooks/useUserEvent';

export function useMyRequests() {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');
  const [requestToCancel, setRequestToCancel] = useState<PassengerRequest | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: qk.passengers.requests(),
    queryFn: async () => {
      const { data } = await fetchMyPassengerRequests();
      return Array.isArray(data) ? data : [];
    },
    staleTime: 30_000,
  });
  const requests = data ?? [];

  const { mutate: mutateCancel, isPending: cancelling } = useMutation({
    mutationKey: mk.rides.cancel('request'),
    mutationFn: (requestId: string) => cancelPassengerRequest(requestId),
    onSuccess: (_, requestId) => {
      queryClient.setQueryData(
        qk.passengers.requests(),
        (old: PassengerRequest[] = []) =>
          old.map((r) =>
            r.request_id === requestId ? { ...r, status: 'cancelled' } : r
          )
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
        (old: PassengerRequest[] = []) =>
          old.map((r) =>
            r.request_id === detail.request_id ? { ...r, status: 'expired' } : r
          )
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
