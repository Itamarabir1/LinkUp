import { useEffect, useState } from 'react';
import { fetchMapsKey } from '../api/geo';
import { GOOGLE_MAPS_API_KEY } from '../config/env';

export function useGoogleMapsKey() {
  const [resolvedKey, setResolvedKey] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (GOOGLE_MAPS_API_KEY) {
      queueMicrotask(() => setResolvedKey(GOOGLE_MAPS_API_KEY));
      return;
    }

    let cancelled = false;
    fetchMapsKey()
      .then(({ data }) => {
        if (cancelled) return;
        if (data?.google_maps_api_key) setResolvedKey(data.google_maps_api_key);
        else setResolvedKey('');
      })
      .catch(() => {
        if (!cancelled) {
          setResolvedKey('');
          setLoadError('לא ניתן לטעון מפתח מפה');
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (resolvedKey === '') {
      queueMicrotask(() => setLoadError('לא הוגדר מפתח מפה'));
    }
  }, [resolvedKey]);

  return { resolvedKey, loadError };
}

