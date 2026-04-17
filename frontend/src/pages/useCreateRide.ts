import { useCallback, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { fetchAddressFromCoords } from '../api/geo';
import {
  parseRideSearchWithAI,
  type AISearchResult,
  type ConversationTurn,
} from '../api/passengers';
import { previewRideRoutes, createRideFromSession } from '../api/rides';
import { useAuth } from '../context/AuthContext';
import type { RidePreviewResponse } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import { apiErr } from '../utils/i18nError';
import type { RouteMapData } from '../components/RouteMapModal';

type CreateRideStatus = 'idle' | 'locating' | 'previewing' | 'creating';

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

/** Semantic reason — pure logic, no i18n dependency */
export type CreateRideFollowUpReason =
  | 'missing_location'
  | 'need_time'
  | 'need_datetime'
  | 'past_or_invalid'
  | null;

export function resolveCreateRideFollowUpReason(ai: AISearchResult): CreateRideFollowUpReason {
  if (!ai.pickup_name || !ai.destination_name) {
    return 'missing_location';
  }
  if (!ai.departure_time) {
    return ai.departure_date ? 'need_time' : 'need_datetime';
  }
  const d = new Date(ai.departure_time);
  if (isNaN(d.getTime()) || d <= new Date()) {
    return 'past_or_invalid';
  }
  return null;
}

export function extractSeatsFromText(text: string): number | null {
  const match = text.match(/(\d+)\s*(מקומות|נוסעים|seats|seat)/i);
  if (!match) return null;
  const n = parseInt(match[1], 10);
  if (isNaN(n)) return null;
  return Math.max(1, Math.min(8, n));
}

function followUpReasonToText(
  reason: CreateRideFollowUpReason,
  followUpFromServer: string | null,
  t: (key: string) => string
): string | null {
  switch (reason) {
    case 'missing_location':
      return followUpFromServer;
    case 'need_time':
      return t('aiCreateFollowUpTime');
    case 'need_datetime':
      return t('aiCreateFollowUpDateTime');
    case 'past_or_invalid':
      return t('aiCreateFollowUpPastTime');
    default:
      return null;
  }
}

export function useCreateRide() {
  const { t } = useTranslation('rides');
  const { groupId } = useParams<{ groupId?: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [originName, setOriginName] = useState('');
  const [destinationName, setDestinationName] = useState('');
  const [selectedDate, setSelectedDate] = useState<Date>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(9, 0, 0, 0);
    return d;
  });
  const [seats, setSeats] = useState(4);
  const [status, setStatus] = useState<CreateRideStatus>('idle');
  const [preview, setPreview] = useState<RidePreviewResponse | null>(null);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(-1);
  const [error, setError] = useState('');
  const [mapPreviewData, setMapPreviewData] = useState<RouteMapData | null>(null);

  const [aiQuery, setAiQuery] = useState('');
  const [aiParsing, setAiParsing] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiResult, setAiResult] = useState<AISearchResult | null>(null);
  const [aiFollowUp, setAiFollowUp] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([]);

  const { claim, isCurrent } = useOperationToken();
  const { claim: claimAiParse, isCurrent: isAiParseCurrent } = useOperationToken();

  const fillOriginFromMyLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('הדפדפן לא תומך במיקום');
      return;
    }
    const token = claim();
    setStatus('locating');
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const { data } = await fetchAddressFromCoords(
            pos.coords.latitude,
            pos.coords.longitude
          );
          if (isCurrent(token)) setOriginName(data.address ?? '');
        } catch (err) {
          if (isCurrent(token)) setError(getApiErrorMessage(err, apiErr('err_geocode_not_found')));
        } finally {
          if (isCurrent(token)) setStatus('idle');
        }
      },
      () => {
        if (isCurrent(token)) {
          setError('לא ניתן לקבל מיקום — בדוק הרשאות');
          setStatus('idle');
        }
      },
      { timeout: 10000 }
    );
  }, [claim, isCurrent]);

  const handleSwap = useCallback(() => {
    setOriginName((prev) => {
      setDestinationName(prev);
      return destinationName;
    });
  }, [destinationName]);

  const parseWithAI = useCallback(async () => {
    const q = aiQuery.trim();
    if (!q) return;

    const token = claimAiParse();
    setAiParsing(true);
    setAiError('');

    try {
      const { data } = await parseRideSearchWithAI({
        query: q,
        conversation_history: conversationHistory,
      });
      if (!isAiParseCurrent(token)) return;

      setAiResult(data);

      if (data.pickup_name) setOriginName(data.pickup_name);
      if (data.destination_name) setDestinationName(data.destination_name);

      if (data.departure_time) {
        const d = new Date(data.departure_time);
        if (!isNaN(d.getTime()) && d > new Date()) {
          setSelectedDate(d);
        }
      }

      if (data.raw_interpretation) {
        const extracted = extractSeatsFromText(data.raw_interpretation);
        if (extracted !== null) setSeats(extracted);
      }

      const reason = resolveCreateRideFollowUpReason(data);
      const followUp = followUpReasonToText(reason, data.follow_up_question, t);
      setAiFollowUp(followUp);

      const assistantContent = data.raw_interpretation?.trim() || '…';
      setConversationHistory((prev) => {
        const next: ConversationTurn[] = [
          ...prev,
          { role: 'user', content: q },
          { role: 'assistant', content: assistantContent },
        ];
        return next.slice(-6);
      });

      if (followUp) setAiQuery('');
    } catch (err: unknown) {
      if (isAiParseCurrent(token)) {
        setAiError(getApiErrorMessage(err, t('aiCreateParseError')));
      }
    } finally {
      if (isAiParseCurrent(token)) setAiParsing(false);
    }
  }, [
    aiQuery,
    claimAiParse,
    conversationHistory,
    isAiParseCurrent,
    setOriginName,
    setDestinationName,
    setSelectedDate,
    setSeats,
    t,
  ]);

  const resetAI = useCallback(() => {
    setAiQuery('');
    setAiParsing(false);
    setAiError('');
    setAiResult(null);
    setAiFollowUp(null);
    setConversationHistory([]);
  }, []);

  const requestPreview = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!user?.user_id) {
        setError('לא זוהה משתמש מחובר. התחבר/י מחדש ונסה/י שוב.');
        return;
      }
      if (!originName.trim() || !destinationName.trim()) {
        setError('יש למלא מוצא ויעד');
        return;
      }
      if (isNaN(selectedDate.getTime()) || selectedDate <= new Date()) {
        setError('יש לבחור זמן יציאה בעתיד');
        return;
      }

      const token = claim();
      setStatus('previewing');
      setError('');
      setPreview(null);

      try {
        const { data } = await previewRideRoutes({
          driver_id: user.user_id,
          origin_name: originName.trim(),
          destination_name: destinationName.trim(),
          departure_time: selectedDate.toISOString(),
          available_seats: seats,
          ...(groupId ? { group_id: groupId } : {}),
        });
        if (!isCurrent(token)) return;
        const routesList = Array.isArray(data.routes) ? data.routes : data.routes ? [data.routes] : [];
        setPreview({ ...data, routes: routesList });
        setSelectedRouteIndex(routesList.length === 1 ? 0 : -1);
      } catch (err) {
        if (isCurrent(token)) setError(getApiErrorMessage(err, apiErr('err_preview_ride')));
      } finally {
        if (isCurrent(token)) setStatus('idle');
      }
    },
    [user, originName, destinationName, selectedDate, seats, groupId, claim, isCurrent]
  );

  const createRide = useCallback(async () => {
    if (!preview?.session_id) return;
    const routesCount = preview.routes?.length ?? 0;
    if (routesCount > 1 && (selectedRouteIndex < 0 || selectedRouteIndex >= routesCount)) {
      setError('יש לבחור מסלול');
      return;
    }
    const token = claim();
    setStatus('creating');
    setError('');
    try {
      await createRideFromSession({
        session_id: preview.session_id,
        selected_route_index: routesCount === 1 ? 0 : selectedRouteIndex,
        ...(groupId ? { group_id: groupId } : {}),
      });
      if (!isCurrent(token)) return;
      setPreview(null);
      navigate(groupId ? `/groups/${groupId}` : '/my-rides', { replace: true });
    } catch (err) {
      if (isCurrent(token)) setError(getApiErrorMessage(err, apiErr('err_create_ride')));
    } finally {
      if (isCurrent(token)) setStatus('idle');
    }
  }, [preview, selectedRouteIndex, groupId, claim, isCurrent, navigate]);

  return {
    groupId,
    originName,
    setOriginName,
    destinationName,
    setDestinationName,
    selectedDate,
    setSelectedDate,
    seats,
    setSeats,
    preview,
    selectedRouteIndex,
    setSelectedRouteIndex,
    error,
    mapPreviewData,
    setMapPreviewData,
    fillOriginFromMyLocation,
    handleSwap,
    requestPreview,
    createRide,
    loading: status === 'previewing',
    creating: status === 'creating',
    locationLoading: status === 'locating',
    aiQuery,
    setAiQuery,
    aiParsing,
    aiError,
    aiResult,
    aiFollowUp,
    conversationHistory,
    parseWithAI,
    resetAI,
  };
}
