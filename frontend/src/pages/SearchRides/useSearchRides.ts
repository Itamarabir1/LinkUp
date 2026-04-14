import { useCallback, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchAddressFromCoords } from '../../api/geo';
import {
  requestRideFromSearch,
  saveSearchAlert,
  searchRides as searchRidesApi,
} from '../../api/passengers';
import { fetchPassengerDriverInfo } from '../../api/rides';
import type { Ride, DriverInfo } from '../../types/api';
import { getApiErrorMessage, getApiStatus } from '../../utils/apiError';

function defaultDepartureDate(): Date {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(9, 0, 0, 0);
  return d;
}

function useOperationToken() {
  const tokenRef = useRef(0);
  const claim = useCallback((): number => {
    tokenRef.current += 1;
    return tokenRef.current;
  }, []);
  const isCurrent = useCallback((token: number): boolean => {
    return tokenRef.current === token;
  }, []);
  return { claim, isCurrent };
}

export function useSearchRides() {
  const { groupId } = useParams<{ groupId?: string }>();
  const { claim: claimLocation, isCurrent: isLocationOpCurrent } = useOperationToken();
  const { claim: claimSearch, isCurrent: isSearchOpCurrent } = useOperationToken();
  const { claim: claimLoadMore, isCurrent: isLoadMoreOpCurrent } = useOperationToken();
  const [pickup, setPickup] = useState('');
  const [destination, setDestination] = useState('');
  const [searchRadius, setSearchRadius] = useState(1);
  const [selectedDate, setSelectedDate] = useState<Date>(defaultDepartureDate);
  const [results, setResults] = useState<Ride[]>([]);
  const [resultsNextCursor, setResultsNextCursor] = useState<string | null>(null);
  const [resultsHasMore, setResultsHasMore] = useState(false);
  const [searching, setSearching] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [locationLoading, setLocationLoading] = useState(false);
  const [driverInfoMap, setDriverInfoMap] = useState<Record<string, DriverInfo>>({});
  const [loadingDriverRideId, setLoadingDriverRideId] = useState<string | null>(null);
  const [sendingRequestRideId, setSendingRequestRideId] = useState<string | null>(null);
  const [requestSuccessRideId, setRequestSuccessRideId] = useState<string | null>(null);
  const [requestErrorRideId, setRequestErrorRideId] = useState<string | null>(null);
  const [requestErrorMessage, setRequestErrorMessage] = useState('');
  const [savingAlert, setSavingAlert] = useState(false);
  const [alertSaved, setAlertSaved] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const fillPickupFromMyLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('הדפדפן לא תומך במיקום');
      return;
    }
    const token = claimLocation();
    setLocationLoading(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { data } = await fetchAddressFromCoords(
            pos.coords.latitude,
            pos.coords.longitude
          );
          if (isLocationOpCurrent(token)) setPickup(data.address ?? '');
        } catch (err) {
          if (isLocationOpCurrent(token))
            setError(getApiErrorMessage(err, 'לא נמצאה כתובת למיקום זה'));
        } finally {
          if (isLocationOpCurrent(token)) setLocationLoading(false);
        }
      },
      () => {
        if (isLocationOpCurrent(token)) {
          setError('לא ניתן לקבל מיקום — בדוק הרשאות');
          setLocationLoading(false);
        }
      },
      { timeout: 10000 }
    );
  }, [claimLocation, isLocationOpCurrent]);

  const handleSwap = useCallback(() => {
    setPickup((currentPickup) => {
      setDestination(currentPickup);
      return destination;
    });
  }, [destination]);

  const buildSearchParams = useCallback((): Record<string, string | number | undefined> => {
    const params: Record<string, string | number | undefined> = {
      pickup_name: pickup.trim(),
      destination_name: destination.trim(),
      search_radius: searchRadius,
      limit: 20,
    };
    if (selectedDate) params.departure_time = selectedDate.toISOString();
    if (groupId) params.group_id = groupId;
    return params;
  }, [pickup, destination, searchRadius, selectedDate, groupId]);

  const search = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!pickup.trim() || !destination.trim()) {
        setError('יש למלא מוצא ויעד');
        return;
      }
      claimLocation();
      const token = claimSearch();
      setError('');
      setSearching(true);
      setResults([]);
      setHasSearched(false);
      setResultsNextCursor(null);
      setResultsHasMore(false);
      setRequestSuccessRideId(null);
      setDriverInfoMap({});
      setAlertSaved(false);
      try {
        const { data } = await searchRidesApi(buildSearchParams());
        if (!isSearchOpCurrent(token)) return;
        setResults(data?.items ?? []);
        setResultsNextCursor(data?.next_cursor ?? null);
        setResultsHasMore(data?.has_more ?? false);
        setHasSearched(true);
      } catch (err: unknown) {
        if (isSearchOpCurrent(token)) setError(getApiErrorMessage(err, 'חיפוש נכשל'));
      } finally {
        if (isSearchOpCurrent(token)) setSearching(false);
      }
    },
    [
      buildSearchParams,
      claimLocation,
      claimSearch,
      destination,
      isSearchOpCurrent,
      pickup,
    ]
  );

  const loadMoreResults = useCallback(async () => {
    if (!resultsNextCursor || loadingMore || !pickup.trim() || !destination.trim()) return;
    const token = claimLoadMore();
    setLoadingMore(true);
    setError('');
    try {
      const params = { ...buildSearchParams(), after: resultsNextCursor };
      const { data } = await searchRidesApi(params);
      if (!isLoadMoreOpCurrent(token)) return;
      const newItems = data?.items ?? [];
      setResults((prev) => [...prev, ...newItems]);
      setResultsNextCursor(data?.next_cursor ?? null);
      setResultsHasMore(data?.has_more ?? false);
    } catch (err: unknown) {
      if (isLoadMoreOpCurrent(token)) setError(getApiErrorMessage(err, 'טעינה נכשלה'));
    } finally {
      if (isLoadMoreOpCurrent(token)) setLoadingMore(false);
    }
  }, [
    buildSearchParams,
    claimLoadMore,
    destination,
    isLoadMoreOpCurrent,
    loadingMore,
    pickup,
    resultsNextCursor,
  ]);

  const saveAlert = async () => {
    if (!pickup.trim() || !destination.trim()) return;
    setSavingAlert(true);
    setError('');
    try {
      await saveSearchAlert({
        pickup_name: pickup.trim(),
        destination_name: destination.trim(),
        requested_departure_time: selectedDate.toISOString(),
        search_radius: searchRadius,
        num_passengers: 1,
        is_notification_active: true,
        ...(groupId ? { group_id: groupId } : {}),
      });
      setAlertSaved(true);
    } catch (err: unknown) {
      const status = getApiStatus(err);
      if (status === 401) {
        setError('פג תוקף ההתחברות – אנא התחבר מחדש כדי לשמור התראה.');
        return;
      }
      setError(getApiErrorMessage(err, 'שמירת ההתראה נכשלה'));
    } finally {
      setSavingAlert(false);
    }
  };

  const fetchDriverInfo = async (rideId: string) => {
    setLoadingDriverRideId(rideId);
    setError('');
    try {
      const { data } = await fetchPassengerDriverInfo(rideId);
      setDriverInfoMap((prev) => ({ ...prev, [rideId]: data }));
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'לא ניתן לטעון פרטי נהג'));
    } finally {
      setLoadingDriverRideId(null);
    }
  };

  const sendRequestToJoin = async (r: Ride) => {
    if (!pickup.trim() || !destination.trim()) {
      setError('נא למלא מוצא ויעד לפני שליחת בקשה');
      return;
    }
    setSendingRequestRideId(r.ride_id);
    setRequestErrorRideId(null);
    setRequestErrorMessage('');
    setError('');
    try {
      await requestRideFromSearch({
        ride_id: r.ride_id,
        pickup_name: pickup.trim(),
        destination_name: destination.trim(),
        num_seats: 1,
      });
      setRequestSuccessRideId(r.ride_id);
    } catch (err: unknown) {
      const status = getApiStatus(err);
      if (status === 401) {
        setError('פג תוקף ההתחברות – אנא התחבר מחדש כדי לשלוח בקשה.');
        return;
      }
      if (status === 409) {
        const msg = getApiErrorMessage(err, 'המקום התמלא. נסה נסיעה אחרת.');
        setRequestErrorRideId(r.ride_id);
        setRequestErrorMessage(msg);
        setError(msg);
        return;
      }
      const msg = getApiErrorMessage(err, 'שליחת הבקשה נכשלה');
      setRequestErrorRideId(r.ride_id);
      setRequestErrorMessage(msg);
      setError(msg);
    } finally {
      setSendingRequestRideId(null);
    }
  };

  return {
    pickup,
    setPickup,
    destination,
    setDestination,
    searchRadius,
    setSearchRadius,
    selectedDate,
    setSelectedDate,
    results,
    resultsHasMore,
    searching,
    loadingMore,
    error,
    locationLoading,
    driverInfoMap,
    loadingDriverRideId,
    sendingRequestRideId,
    requestSuccessRideId,
    requestErrorRideId,
    requestErrorMessage,
    fillPickupFromMyLocation,
    handleSwap,
    search,
    loadMoreResults,
    fetchDriverInfo,
    sendRequestToJoin,
    groupId,
    savingAlert,
    alertSaved,
    saveAlert,
    hasSearched,
  };
}
