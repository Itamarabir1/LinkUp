import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { fetchAddressFromCoords } from '../../api/geo';
import {
  parseRideSearchWithAI,
  saveSearchAlert,
  searchRides as searchRidesApi,
  type AISearchResult,
  type ConversationTurn,
} from '../../api/passengers';
import { fetchPassengerDriverInfo } from '../../api/rides';
import type { Ride, DriverInfo } from '../../types/api';
import { getApiErrorMessage, getApiStatus } from '../../utils/apiError';
import { apiErr } from '../../utils/i18nError';
import { useJoinRide } from './useJoinRide';

/** AI response may include these before `AISearchResult` in passengers.ts is extended. */
export type AIParsedSearch = AISearchResult & {
  departure_time_to?: string | null;
  departure_date?: string | null;
  destination_radius?: number | null;
};

export type SearchMode = 'datetime' | 'date_only' | 'time_range';

/**
 * Build GET /search-rides params only from AI output + groupId (no React state timing issues).
 * Returns null when auto-search must not run.
 */
export function buildParamsFromAiResult(
  ai: AIParsedSearch,
  ctx: { groupId?: string | null }
): Record<string, string | number | undefined> | null {
  const pickup = ai.pickup_name?.trim() ?? '';
  const dest = ai.destination_name?.trim() ?? '';
  if (!pickup || !dest || ai.needs_clarification) return null;

  const hasAnchor = Boolean(
    ai.departure_date ||
      ai.departure_time ||
      (ai.departure_time && ai.departure_time_to)
  );
  if (!hasAnchor) return null;

  const params: Record<string, string | number | undefined> = {
    pickup_name: pickup,
    destination_name: dest,
    search_radius:
      ai.search_radius != null && !Number.isNaN(Number(ai.search_radius))
        ? Math.min(50, Math.max(1, Math.round(Number(ai.search_radius))))
        : 3,
    limit: 20,
  };
  if (ctx.groupId) params.group_id = ctx.groupId;

  if (ai.departure_time) {
    const t = new Date(ai.departure_time);
    if (!Number.isNaN(t.getTime())) params.departure_time = t.toISOString();
  }
  if (ai.departure_time_to) {
    const t2 = new Date(ai.departure_time_to);
    if (!Number.isNaN(t2.getTime())) params.departure_time_to = t2.toISOString();
  }
  if (ai.departure_date && !ai.departure_time) {
    params.departure_date = ai.departure_date;
    const d0 = new Date(`${ai.departure_date}T00:00:00`);
    if (!Number.isNaN(d0.getTime())) params.departure_time = d0.toISOString();
  }
  if (ai.destination_radius != null && !Number.isNaN(Number(ai.destination_radius))) {
    params.destination_radius = Math.min(50, Math.max(0.1, Number(ai.destination_radius)));
  }
  return params;
}

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
  const { t } = useTranslation('rides');
  const { groupId } = useParams<{ groupId?: string }>();
  const { claim: claimLocation, isCurrent: isLocationOpCurrent } = useOperationToken();
  const { claim: claimSearch, isCurrent: isSearchOpCurrent } = useOperationToken();
  const { claim: claimLoadMore, isCurrent: isLoadMoreOpCurrent } = useOperationToken();
  const { claim: claimAiParse, isCurrent: isAiParseCurrent } = useOperationToken();
  const {
    sendingRequestRideId,
    requestSuccessRideId,
    requestErrorRideId,
    requestErrorMessage,
    sendRequestToJoin: joinRide,
    resetJoinState,
  } = useJoinRide();
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
  const [savingAlert, setSavingAlert] = useState(false);
  const [alertSaved, setAlertSaved] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const [aiQuery, setAiQuery] = useState('');
  const [aiParsing, setAiParsing] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiResult, setAiResult] = useState<AISearchResult | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([]);
  const [searchMode, setSearchMode] = useState<SearchMode>('datetime');
  const [selectedDateTo, setSelectedDateTo] = useState<Date | null>(null);
  const [departureDateOnly, setDepartureDateOnly] = useState<Date | null>(null);
  const [destinationRadius, setDestinationRadius] = useState<number | null>(null);

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
            setError(getApiErrorMessage(err, apiErr('err_geocode_not_found')));
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

  const resetAI = useCallback(() => {
    setAiQuery('');
    setAiParsing(false);
    setAiError('');
    setAiResult(null);
    setConversationHistory([]);
    setSelectedDateTo(null);
    setDepartureDateOnly(null);
    setDestinationRadius(null);
    setSearchMode('datetime');
  }, []);

  const parseWithAI = useCallback(async () => {
    const q = aiQuery.trim();
    if (!q) {
      setAiError(t('aiEmptyQuery'));
      return;
    }
    const token = claimAiParse();
    setAiParsing(true);
    setAiError('');
    try {
      const { data } = await parseRideSearchWithAI({
        query: q,
        conversation_history: conversationHistory,
      });
      if (!isAiParseCurrent(token)) return;
      const parsed = data as AIParsedSearch;
      setAiResult(data);
      if (data.pickup_name) setPickup(data.pickup_name);
      if (data.destination_name) setDestination(data.destination_name);
      if (data.search_radius != null && !Number.isNaN(Number(data.search_radius))) {
        const r = Math.round(Number(data.search_radius));
        setSearchRadius(Math.min(50, Math.max(1, r)));
      }
      if (parsed.destination_radius != null && !Number.isNaN(Number(parsed.destination_radius))) {
        setDestinationRadius(
          Math.min(50, Math.max(0.1, Number(parsed.destination_radius)))
        );
      } else {
        setDestinationRadius(null);
      }

      if (parsed.departure_time && parsed.departure_time_to) {
        setSearchMode('time_range');
        const a = new Date(parsed.departure_time);
        const b = new Date(parsed.departure_time_to);
        if (!Number.isNaN(a.getTime())) setSelectedDate(a);
        if (!Number.isNaN(b.getTime())) setSelectedDateTo(b);
        setDepartureDateOnly(null);
      } else if (parsed.departure_date && !parsed.departure_time) {
        setSearchMode('date_only');
        const [yy, mm, dd] = parsed.departure_date.split('-').map(Number);
        if (yy && mm && dd) {
          const dOnly = new Date(yy, mm - 1, dd, 9, 0, 0, 0);
          setDepartureDateOnly(dOnly);
          setSelectedDate(dOnly);
        }
        setSelectedDateTo(null);
      } else if (parsed.departure_time) {
        setSearchMode('datetime');
        const d = new Date(parsed.departure_time);
        if (!Number.isNaN(d.getTime())) setSelectedDate(d);
        setSelectedDateTo(null);
        setDepartureDateOnly(null);
      } else {
        setSearchMode('datetime');
        setSelectedDateTo(null);
        setDepartureDateOnly(null);
      }

      const assistantContent =
        data.follow_up_question?.trim() ||
        data.raw_interpretation?.trim() ||
        '';
      setConversationHistory((prev) => {
        const next: ConversationTurn[] = [
          ...prev,
          { role: 'user', content: q },
          { role: 'assistant', content: assistantContent || '…' },
        ];
        return next.slice(-6);
      });
      if (data.follow_up_question) setAiQuery('');

      const autoParams = buildParamsFromAiResult(parsed, { groupId });
      if (autoParams) {
        const searchToken = claimSearch();
        setError('');
        setSearching(true);
        setResults([]);
        setHasSearched(false);
        setResultsNextCursor(null);
        setResultsHasMore(false);
        resetJoinState();
        setDriverInfoMap({});
        setAlertSaved(false);
        try {
          const { data: searchData } = await searchRidesApi(autoParams);
          if (!isSearchOpCurrent(searchToken)) return;
          setResults(searchData?.items ?? []);
          setResultsNextCursor(searchData?.next_cursor ?? null);
          setResultsHasMore(searchData?.has_more ?? false);
          setHasSearched(true);
        } catch (err: unknown) {
          if (isSearchOpCurrent(searchToken))
            setError(getApiErrorMessage(err, apiErr('err_search_rides')));
        } finally {
          if (isSearchOpCurrent(searchToken)) setSearching(false);
        }
      }
    } catch (err: unknown) {
      if (isAiParseCurrent(token)) {
        setAiError(getApiErrorMessage(err, t('aiParseError')));
      }
    } finally {
      if (isAiParseCurrent(token)) setAiParsing(false);
    }
  }, [
    aiQuery,
    claimAiParse,
    claimSearch,
    conversationHistory,
    groupId,
    isAiParseCurrent,
    isSearchOpCurrent,
    resetJoinState,
    t,
  ]);

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
      resetJoinState();
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
        if (isSearchOpCurrent(token)) setError(getApiErrorMessage(err, apiErr('err_search_rides')));
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
      resetJoinState,
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
      if (isLoadMoreOpCurrent(token)) setError(getApiErrorMessage(err, apiErr('err_load_more')));
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
        setError(apiErr('err_save_alert_session'));
        return;
      }
      setError(getApiErrorMessage(err, apiErr('err_save_alert')));
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
      setError(getApiErrorMessage(err, apiErr('err_load_driver')));
    } finally {
      setLoadingDriverRideId(null);
    }
  };

  const sendRequestToJoin = useCallback(
    async (r: Ride) => {
      if (!pickup.trim() || !destination.trim()) {
        setError('יש למלא מוצא ויעד לפני שליחת בקשה');
        return;
      }
      setError('');
      await joinRide(
        r,
        pickup,
        destination,
        () => {},
        (msg) => setError(msg),
        () => setError('פג תוקף ההתחברות'),
      );
    },
    [pickup, destination, joinRide],
  );

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
    aiQuery,
    setAiQuery,
    aiParsing,
    aiError,
    aiResult,
    conversationHistory,
    parseWithAI,
    resetAI,
    searchMode,
    setSearchMode,
    selectedDateTo,
    setSelectedDateTo,
    departureDateOnly,
    setDepartureDateOnly,
    destinationRadius,
    setDestinationRadius,
  };
}
