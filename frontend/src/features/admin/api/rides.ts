import { api } from '../../../api/client';

export type AdminRideRow = {
  ride_id: string;
  driver_id: string;
  driver_name: string;
  origin_name: string | null;
  destination_name: string | null;
  departure_time: string | null;
  status: string;
  available_seats: number;
  group_id: string | null;
};

export function fetchAdminRides(params?: { status?: string; limit?: number }) {
  return api.get<AdminRideRow[]>('/admin/rides', { params });
}

export function postAdminCancelRide(rideId: string) {
  return api.post<{ ok: boolean; ride_id: string }>(`/admin/rides/${rideId}/cancel`);
}
