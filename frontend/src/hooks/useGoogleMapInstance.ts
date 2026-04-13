import { useEffect, useRef, useState } from 'react';
import { loadGoogleMaps } from '../lib/loadGoogleMaps';

const DEFAULT_CENTER = { lat: 32.0853, lng: 34.7818 };

export function useGoogleMapInstance(
  containerRef: React.RefObject<HTMLDivElement | null>,
  resolvedKey: string | null
) {
  const [map, setMap] = useState<google.maps.Map | null>(null);
  const scriptLoadedRef = useRef(!!window.google?.maps);
  const [scriptLoaded, setScriptLoaded] = useState(!!window.google?.maps);
  const [loadError, setLoadError] = useState<string | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);

  useEffect(() => {
    if (resolvedKey === null) return;
    if (!resolvedKey) {
      queueMicrotask(() => setLoadError('לא הוגדר מפתח מפה'));
      return;
    }
    queueMicrotask(() => setLoadError(null));

    if (window.google?.maps) {
      scriptLoadedRef.current = true;
      queueMicrotask(() => setScriptLoaded(true));
      return;
    }

    loadGoogleMaps(
      resolvedKey,
      () => {
        scriptLoadedRef.current = true;
        setScriptLoaded(true);
      },
      () => setLoadError('שגיאה בטעינת Google Maps')
    );
  }, [resolvedKey]);

  useEffect(() => {
    if (!resolvedKey || !scriptLoaded || !window.google?.maps || !containerRef.current) return;

    const el = containerRef.current;
    if (!document.contains(el)) return;

    const m = new google.maps.Map(el, {
      center: DEFAULT_CENTER,
      zoom: 10,
      mapId: import.meta.env.VITE_GOOGLE_MAPS_MAP_ID ?? 'linkup_map',
      mapTypeControl: false,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
    });
    mapRef.current = m;
    setMap(m);

    const resize = () => {
      if (window.google?.maps?.event) {
        window.google.maps.event.trigger(m, 'resize');
      }
    };
    requestAnimationFrame(() => {
      requestAnimationFrame(resize);
    });
    const t = window.setTimeout(resize, 300);

    return () => {
      window.clearTimeout(t);
      mapRef.current = null;
      setMap(null);
    };
  }, [scriptLoaded, resolvedKey, containerRef]);

  return { map, loadError };
}

