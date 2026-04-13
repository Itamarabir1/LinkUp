import { useState } from 'react';
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

export function useSearchRides() {
  const { groupId } = useParams<{ groupId?: string }>();
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

  const fillPickupFromMyLocation = () => {
    if (!navigator.geolocation) {
      setError('הדפדפן לא תומך במיקום');
      return;
    }
    setLocationLoading(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        try {
          const { data } = await fetchAddressFromCoords(lat, lon);
          setPickup(data.address ?? '');
        } catch (err) {
          setError(getApiErrorMessage(err, 'לא נמצאה כתובת למיקום זה'));
        } finally {
          setLocationLoading(false);
        }
      },
      () => {
        setError('לא ניתן לקבל מיקום – בדוק הרשאות');
        setLocationLoading(false);
      },
      { timeout: 10000 }
    );
  };

  const handleSwap = () => {
    setPickup(destination);
    setDestination(pickup);
  };

  const buildSearchParams = (): Record<string, string | number | undefined> => {
    const params: Record<string, string | number | undefined> = {
      pickup_name: pickup.trim(),
      destination_name: destination.trim(),
      search_radius: searchRadius,
      limit: 20,
    };
    if (selectedDate) params.departure_time = selectedDate.toISOString();
    if (groupId) params.group_id = groupId;
    return params;
  };

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pickup.trim() || !destination.trim()) {
      setError('נא למלא מוצא ויעד');
      return;
    }
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
      setResults(data?.items ?? []);
      setResultsNextCursor(data?.next_cursor ?? null);
      setResultsHasMore(data?.has_more ?? false);
      setHasSearched(true);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'חיפוש נכשל'));
    } finally {
      setSearching(false);
    }
  };

  const loadMoreResults = async () => {
    if (!resultsNextCursor || loadingMore || !pickup.trim() || !destination.trim()) return;
    setLoadingMore(true);
    setError('');
    try {
      const params = { ...buildSearchParams(), after: resultsNextCursor };
      const { data } = await searchRidesApi(params);
      const newItems = data?.items ?? [];
      setResults((prev) => [...prev, ...newItems]);
      setResultsNextCursor(data?.next_cursor ?? null);
      setResultsHasMore(data?.has_more ?? false);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'טעינה נכשלה'));
    } finally {
      setLoadingMore(false);
    }
  };

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
