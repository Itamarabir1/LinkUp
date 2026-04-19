/**
 * Hook for joining a ride from search results.
 * Handles idempotency key lifecycle and error mapping.
 * Extracted from useSearchRides for single responsibility.
 */
import { useRef, useState } from 'react';
import { requestRideFromSearch } from '../../api/passengers';
import type { Ride } from '../../types/api';
import { getApiErrorMessage, getApiStatus } from '../../utils/apiError';
import { apiErr } from '../../utils/i18nError';

interface UseJoinRideResult {
  sendingRequestRideId: string | null;
  requestSuccessRideId: string | null;
  requestErrorRideId: string | null;
  requestErrorMessage: string;
  sendRequestToJoin: (
    ride: Ride,
    pickup: string,
    destination: string,
    onSuccess: () => void,
    onError: (msg: string) => void,
    onAuthError: () => void,
  ) => Promise<void>;
  resetJoinState: () => void;
}

export function useJoinRide(): UseJoinRideResult {
  const idempotencyKeyRef = useRef<string | null>(null);
  const [sendingRequestRideId, setSendingRequestRideId] = useState<string | null>(null);
  const [requestSuccessRideId, setRequestSuccessRideId] = useState<string | null>(null);
  const [requestErrorRideId, setRequestErrorRideId] = useState<string | null>(null);
  const [requestErrorMessage, setRequestErrorMessage] = useState('');

  const sendRequestToJoin = async (
    r: Ride,
    pickup: string,
    destination: string,
    onSuccess: () => void,
    onError: (msg: string) => void,
    onAuthError: () => void,
  ) => {
    setSendingRequestRideId(r.ride_id);
    setRequestErrorRideId(null);
    setRequestErrorMessage('');

    try {
      if (idempotencyKeyRef.current === null) {
        idempotencyKeyRef.current = crypto.randomUUID();
      }
      await requestRideFromSearch(
        {
          ride_id: r.ride_id,
          pickup_name: pickup.trim(),
          destination_name: destination.trim(),
          num_seats: 1,
        },
        idempotencyKeyRef.current,
      );
      idempotencyKeyRef.current = null;
      setRequestSuccessRideId(r.ride_id);
      onSuccess();
    } catch (err: unknown) {
      const status = getApiStatus(err);
      if (status === 401) {
        onAuthError();
        return;
      }
      const msg =
        status === 409
          ? getApiErrorMessage(err, apiErr('err_ride_full'))
          : getApiErrorMessage(err, apiErr('err_join_request'));
      setRequestErrorRideId(r.ride_id);
      setRequestErrorMessage(msg);
      onError(msg);
    } finally {
      setSendingRequestRideId(null);
    }
  };

  const resetJoinState = () => {
    idempotencyKeyRef.current = null;
    setSendingRequestRideId(null);
    setRequestSuccessRideId(null);
    setRequestErrorRideId(null);
    setRequestErrorMessage('');
  };

  return {
    sendingRequestRideId,
    requestSuccessRideId,
    requestErrorRideId,
    requestErrorMessage,
    sendRequestToJoin,
    resetJoinState,
  };
}
