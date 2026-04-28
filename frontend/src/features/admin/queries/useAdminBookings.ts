import { useQuery } from '@tanstack/react-query';
import { qk } from '../../../api/queryKeys';
import { fetchAdminBookings } from '../api/bookings';

export function useAdminBookings(params?: {
  status?: string;
  ride_id?: string;
  passenger_id?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: qk.admin.bookings(params),
    queryFn: async () => {
      const { data } = await fetchAdminBookings(params);
      return data;
    },
  });
}
