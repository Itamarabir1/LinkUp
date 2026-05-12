import { api } from './client';
import type { RideManifestResponse } from './generated/types/rideManifestResponse';
import type { BookingRow } from '../pages/MyBookings/myBookings.types';
import type {
  DriverActiveResponse,
  DriverHistoryResponse,
  PassengerActiveResponse,
  PassengerHistoryResponse,
} from '../types/api';

export interface PaginatedBookingsResponse {
  items: BookingRow[];
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
}

export function fetchMyBookings(params?: { limit?: number; after?: string; status?: string }) {
  return api.get<PaginatedBookingsResponse>('/bookings/my-bookings', {
    params: {
      limit: params?.limit ?? 20,
      after: params?.after || undefined,
      status: params?.status,
    },
  });
}

export function fetchDriverActive() {
  return api.get<DriverActiveResponse>('/bookings/driver-summary/active');
}

export function fetchDriverHistory(params?: { limit?: number; after?: string | null }) {
  return api.get<DriverHistoryResponse>('/bookings/driver-summary/history', {
    params: { limit: params?.limit ?? 20, after: params?.after || undefined },
  });
}

export function fetchPassengerActive() {
  return api.get<PassengerActiveResponse>('/bookings/passenger-summary/active');
}

export function fetchPassengerHistory(params?: { limit?: number; after?: string | null }) {
  return api.get<PassengerHistoryResponse>('/bookings/passenger-summary/history', {
    params: { limit: params?.limit ?? 20, after: params?.after || undefined },
  });
}

export type RideManifestPassenger = {
  booking_id: string;
  passenger_name: string;
  num_seats: number;
  status: string;
  pickup_name?: string | null;
  pickup_time?: string | null;
  destination_name?: string | null;
};

export function fetchRideManifest(rideId: string, opts?: { signal?: AbortSignal }) {
  return api.get<RideManifestResponse>(`/bookings/ride/${rideId}/manifest`, { signal: opts?.signal });
}

export function approveBooking(bookingId: string) {
  return api.patch(`/bookings/${bookingId}/approve`, {});
}

export function rejectBooking(bookingId: string) {
  return api.patch(`/bookings/${bookingId}/reject`, {});
}

export function cancelPassengerBooking(bookingId: string) {
  return api.post(`/bookings/${bookingId}/cancel`);
}

export type BookingLocationPayload = {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
};

export function postDriverBookingLocation(bookingId: string, payload: BookingLocationPayload) {
  return api.post(`/bookings/${bookingId}/location`, payload, { timeout: 5000 });
}

export function postPassengerBookingLocation(bookingId: string, payload: BookingLocationPayload) {
  return api.post(`/bookings/${bookingId}/passenger-location`, payload, { timeout: 5000 });
}
