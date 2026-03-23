import { api } from './client';
import type { BookingRow } from '../pages/MyBookings/myBookings.types';

export function fetchMyBookings(userId: string, limit = 50) {
  return api.get<BookingRow[]>('/bookings/my-bookings', {
    params: { user_id: userId, limit },
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

export function fetchRideManifest(rideId: string, driverId: string) {
  return api.get<{ passengers: RideManifestPassenger[] }>(`/bookings/ride/${rideId}/manifest`, {
    params: { driver_id: driverId },
  });
}

export function approveBooking(bookingId: string, driverId: string) {
  return api.patch(`/bookings/${bookingId}/approve`, {}, { params: { driver_id: driverId } });
}

export function rejectBooking(bookingId: string, driverId: string) {
  return api.patch(`/bookings/${bookingId}/reject`, {}, { params: { driver_id: driverId } });
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
