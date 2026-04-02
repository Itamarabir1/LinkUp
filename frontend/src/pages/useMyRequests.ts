import { useCallback, useEffect, useState } from 'react';
import { cancelPassengerRequest, fetchMyPassengerRequests } from '../api/passengers';
import type { PassengerRequest } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';

export function useMyRequests() {
  const [requests, setRequests] = useState<PassengerRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [requestToCancel, setRequestToCancel] = useState<PassengerRequest | null>(null);
  const [cancelling, setCancelling] = useState(false);

  const fetchRequests = useCallback(async () => {
    try {
      const { data } = await fetchMyPassengerRequests();
      setRequests(Array.isArray(data) ? data : []);
      setError('');
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינת בקשות נכשלה'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchRequests();
  }, [fetchRequests]);

  useEffect(() => {
    const onUserEvent = (evt: Event) => {
      const detail = (evt as CustomEvent<{ event?: string; request_id?: string }>).detail;
      if (!detail?.event || !detail.request_id) return;
      if (detail.event === 'REQUEST_EXPIRED') {
        setRequests((prev) =>
          prev.map((r) =>
            r.request_id === detail.request_id ? { ...r, status: 'expired' } : r
          )
        );
      }
    };
    window.addEventListener('linkup:user-event', onUserEvent as EventListener);
    return () => window.removeEventListener('linkup:user-event', onUserEvent as EventListener);
  }, []);

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
    loading,
    error,
    requestToCancel,
    setRequestToCancel,
    cancelling,
    confirmCancelRequest,
  };
}
