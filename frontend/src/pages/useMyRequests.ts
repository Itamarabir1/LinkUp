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
      const all = Array.isArray(data) ? data : [];
      setRequests(all.filter((r) => r.status !== 'cancelled'));
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

  const confirmCancelRequest = useCallback(async () => {
    if (!requestToCancel) return;
    setCancelling(true);
    setError('');
    try {
      await cancelPassengerRequest(requestToCancel.request_id);
      setRequests((prev) => prev.filter((r) => r.request_id !== requestToCancel.request_id));
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
