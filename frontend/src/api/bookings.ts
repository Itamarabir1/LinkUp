import { api } from './client';
import type { BookingRow } from '../pages/MyBookings/myBookings.types';

export function fetchMyBookings(limit = 50, status?: string) {
  return api.get<BookingRow[]>('/bookings/my-bookings', {
    params: { limit, status },
  });
}

/** Backend aggregated driver view — replaces N× manifest + rides/me. */
export type DriverSummaryPassenger = {
  booking_id: string;
  passenger_id: string;
  passenger_name: string;
  phone: string;
  num_seats: number;
  whatsapp_link?: string | null;
  status: string;
  pickup_name?: string | null;
  pickup_time?: string | null;
  destination_name?: string | null;
};

export type DriverSummaryRide = {
  ride_id: string;
  origin_name: string | null;
  destination_name: string | null;
  departure_time: string;
  estimated_arrival_time: string | null;
  available_seats: number;
  price: number;
  status: string;
  group_id?: string | null;
  group_name?: string | null;
  passengers: DriverSummaryPassenger[];
};

export type DriverSummaryResponse = { rides: DriverSummaryRide[] };

export function fetchDriverBookingSummary() {
  return api.get<DriverSummaryResponse>('/bookings/driver-summary');
}

/** Backend aggregated passenger view — replaces N× ride + driver-info. */
export type PassengerSummaryRow = {
  booking_id: string;
  booking_status: string;
  ride_id: string;
  origin_name: string | null;
  destination_name: string | null;
  departure_time: string;
  estimated_arrival_time: string | null;
  ride_status: string;
  group_id?: string | null;
  group_name?: string | null;
  driver: { full_name: string; phone_number?: string | null } | null;
};

export type PassengerSummaryResponse = { bookings: PassengerSummaryRow[] };

export function fetchPassengerBookingSummary() {
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
