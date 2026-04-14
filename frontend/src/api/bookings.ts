import { api } from './client';
import type { BookingRow } from '../pages/MyBookings/myBookings.types';
import type { DriverSummaryResponse, PassengerSummaryResponse } from '../types/api';

export function fetchMyBookings(limit = 50, status?: string) {
  return api.get<BookingRow[]>('/bookings/my-bookings', {
    params: { limit, status },
  });
}

export function fetchDriverSummary() {
  return api.get<DriverSummaryResponse>('/bookings/driver-summary');
}

export function fetchPassengerSummary() {
  return api.get<PassengerSummaryResponse>('/bookings/passenger-summary');
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

export function fetchRideManifest(rideId: string) {
  return api.get<{ passengers: RideManifestPassenger[] }>(`/bookings/ride/${rideId}/manifest`);
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
