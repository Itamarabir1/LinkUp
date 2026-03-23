import { api } from './client';
import type { PassengerRequest, RideSearchResponse } from '../types/api';

export function fetchMyPassengerRequests() {
  return api.get<PassengerRequest[]>('/passenger/passengers/me');
}

export function cancelPassengerRequest(requestId: string) {
  return api.delete(`/passenger/passengers/${requestId}/cancel`);
}

export function searchRides(params: Record<string, string | number | undefined>) {
  return api.get<RideSearchResponse>('/passenger/passengers/search-rides', { params });
}

export function requestRideFromSearch(body: {
  ride_id: string;
  pickup_name: string;
  destination_name: string;
  num_seats: number;
}) {
  return api.post('/passenger/passengers/request-ride-from-search', body);
}
