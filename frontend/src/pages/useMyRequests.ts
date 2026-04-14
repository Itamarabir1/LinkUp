import { useCallback, useEffect, useState } from 'react';
import { cancelPassengerRequest, fetchMyPassengerRequests } from '../api/passengers';
import type { PassengerRequest } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import { useUserEvent } from '../hooks/useUserEvent';

type RequestsStatus = 'loading' | 'idle' | 'error';

export function useMyRequests() {
  const [requests, setRequests] = useState<PassengerRequest[]>([]);
  const [fetchStatus, setFetchStatus] = useState<RequestsStatus>('loading');
  const [error, setError] = useState('');
  const [requestToCancel, setRequestToCancel] = useState<PassengerRequest | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const fetchRequests = useCallback(async () => {
    try {
      const { data } = await fetchMyPassengerRequests();
      setRequests(Array.isArray(data) ? data : []);
      setError('');
      setFetchStatus('idle');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינת בקשות נכשלה'));
      setFetchStatus('error');
    }
  }, []);

  useEffect(() => {
    void fetchRequests();
  }, [fetchRequests]);

  useUserEvent(
    'REQUEST_EXPIRED',
    useCallback((detail) => {
      if (!detail.request_id) return;
      setRequests((prev) =>
        prev.map((r) =>
          r.request_id === detail.request_id ? { ...r, status: 'expired' } : r
        )
      );
    }, [])
  );

  const confirmCancelRequest = useCallback(async () => {
    if (!requestToCancel) return;
    setCancelling(true);
    setError('');
    try {
      await cancelPassengerRequest(requestToCancel.request_id);
      setRequests((prev) =>
        prev.map((r) =>
          r.request_id === requestToCancel.request_id ? { ...r, status: 'cancelled' } : r
        )
      );
      setRequestToCancel(null);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'ביטול הבקשה נכשל'));
    } finally {
      setCancelling(false);
    }
  }, [requestToCancel]);

  return {
    requests,
    loading: fetchStatus === 'loading',
    error,
    requestToCancel,
    setRequestToCancel,
    cancelling,
    confirmCancelRequest,
  };
}
