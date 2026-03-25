import { api } from '../../../api/client';

export function fetchAdminRide(ride_id: string) {
  return api.get(`/admin/rides/${ride_id}`);
}

export function fetchAdminBooking(booking_id: string) {
  return api.get(`/admin/bookings/${booking_id}`);
}
