import { useQuery } from '@tanstack/react-query';
import { qk } from '../api/queryKeys';
import { fetchMapsKey } from '../api/geo';
import { GOOGLE_MAPS_API_KEY } from '../config/env';

export function useGoogleMapsKey() {
  const { data, error, isPending } = useQuery({
    queryKey: qk.geo.mapsKey(),
    queryFn: async () => {
      if (GOOGLE_MAPS_API_KEY) return GOOGLE_MAPS_API_KEY;
      const { data } = await fetchMapsKey();
      return data?.google_maps_api_key ?? '';
    },
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 2,
  });

  return {
    resolvedKey: isPending ? null : (data ?? null),
    loadError: error ? 'לא ניתן לטעון מפתח מפה' : data === '' ? 'לא הוגדר מפתח מפה' : null,
  };
}

