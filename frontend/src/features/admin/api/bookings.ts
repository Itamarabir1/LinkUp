import { api } from '../../../api/client';

export type AdminBookingRow = {
  booking_id: string;
  ride_id: string;
  passenger_id: string;
  request_id: string | null;
  num_seats: number;
  pickup_name: string | null;
  pickup_time: string | null;
  status: string;
  created_at: string | null;
  updated_at: string | null;
};

export type AdminPaginated<T> = {
  items: T[];
  limit: number;
  offset: number;
  total: number;
  next_offset: number | null;
};

export function fetchAdminBookings(params?: {
  status?: string;
  ride_id?: string;
  passenger_id?: string;
  limit?: number;
  offset?: number;
}) {
  return api.get<AdminPaginated<AdminBookingRow>>('/admin/bookings', { params });
}
