import type { AxiosResponse } from 'axios';
import { api } from './client';
import type { PassengerRequest, RideSearchResponse } from '../types/api';

export type ConversationTurn = {
  role: 'user' | 'assistant';
  content: string;
};

export type AISearchQuery = {
  query: string;
  conversation_history?: ConversationTurn[];
};

export type AISearchResult = {
  pickup_name: string | null;
  destination_name: string | null;
  departure_time: string | null;
  departure_time_to: string | null;
  departure_date: string | null;
  destination_radius: number | null;
  search_radius: number | null;
  confidence: number;
  raw_interpretation: string;
  needs_clarification: boolean;
  missing_fields: string[];
  ambiguity_reasons: string[];
  follow_up_question: string | null;
};

export function parseRideSearchWithAI(body: AISearchQuery) {
  return api.post<AISearchResult>('/passenger/passengers/ai-parse-search', body);
}

export type SaveSearchAlertBody = {
  pickup_name: string;
  destination_name: string;
  requested_departure_time: string;
  search_radius: number;
  num_passengers: number;
  is_notification_active: boolean;
  group_id?: string | null;
};

export function saveSearchAlert(body: SaveSearchAlertBody) {
  return api.post<PassengerRequest>('/passenger/passengers/', body);
}

export function fetchMyPassengerRequests() {
  return api.get<PassengerRequest[]>('/passenger/passengers/me');
}

export function cancelPassengerRequest(requestId: string) {
  return api.delete(`/passenger/passengers/${requestId}/cancel`);
}

export function searchRides(params: Record<string, string | number | undefined>) {
  return api.get<RideSearchResponse>('/passenger/passengers/search-rides', { params });
}

export async function requestRideFromSearch(
  body: {
    ride_id: string;
    pickup_name: string;
    destination_name: string;
    num_seats: number;
    request_id?: string;
  },
  idempotencyKey?: string
): Promise<AxiosResponse> {
  const key = idempotencyKey ?? crypto.randomUUID();
  return api.post('/passenger/passengers/request-ride-from-search', body, {
    headers: {
      'Idempotency-Key': key,
    },
  });
}
