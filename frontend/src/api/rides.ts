import { api } from './client';
import type {
  DriverInfo,
  PaginatedRidesResponse,
  Ride,
  RidePreviewResponse,
} from '../types/api';

export function fetchMyRides(params?: { status?: string; limit?: number; after?: string }) {
  return api.get<PaginatedRidesResponse>('/rides/me', {
    params: {
      status: params?.status,
      limit: params?.limit ?? 20,
      after: params?.after,
    },
  });
}

export function fetchRideById(rideId: string) {
  return api.get<Ride>(`/rides/${rideId}`);
}

export function cancelRide(rideId: string) {
  return api.delete(`/rides/${rideId}/cancel`);
}

export function startRide(rideId: string) {
  return api.post(`/rides/${rideId}/start`);
}

export function endRide(rideId: string) {
  return api.post(`/rides/${rideId}/end`);
}

export type PreviewRoutesBody = {
  driver_id: string;
  origin_name: string;
  destination_name: string;
  departure_time: string;
  available_seats: number;
  group_id?: string;
};

export function previewRideRoutes(body: PreviewRoutesBody) {
  return api.post<RidePreviewResponse>('/rides/preview-routes', body);
}

export function createRideFromSession(body: {
  session_id: string;
  selected_route_index: number;
  group_id?: string;
}) {
  return api.post('/rides/', body);
}

export function fetchPassengerDriverInfo(rideId: string) {
  return api.get<DriverInfo>(`/passenger/rides/${rideId}/driver-info`);
}
