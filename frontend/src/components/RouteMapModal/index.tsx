import { useEffect, useRef, useState } from 'react';
import { api } from '../../api/client';
import { GOOGLE_MAPS_API_KEY } from '../../config/env';
import styles from './RouteMapModal.module.css';

declare global {
  interface Window {
    __linkupMapsInit?: () => void;
  }
}

export type RouteMapData = {
  originCoords: number[];
  destinationCoords: number[];
  routeCoords: number[][];
  summary: string;
};

type RouteMapModalProps = {
  data: RouteMapData | null;
  onClose: () => void;
};

function coordsToLatLng(c: number[]): { lat: number; lng: number } {
  const [lat, lng] = c.length >= 2 ? c : [0, 0];
  return { lat, lng };
}

function pathToLatLngs(coords: number[][]): { lat: number; lng: number }[] {
  return coords.map((c) => coordsToLatLng(c)).filter((p) => p.lat !== 0 || p.lng !== 0);
}

export default function RouteMapModal({ data, onClose }: RouteMapModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const [resolvedKey, setResolvedKey] = useState<string | null>(null);
  const [scriptLoaded, setScriptLoaded] = useState(!!window.google?.maps);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    if (GOOGLE_MAPS_API_KEY) {
      queueMicrotask(() => setResolvedKey(GOOGLE_MAPS_API_KEY));
      return;
    }
    let cancelled = false;
    api
      .get<{ google_maps_api_key: string }>('/geo/maps-key')
      .then(({ data }) => {
        if (!cancelled && data?.google_maps_api_key) {
          setResolvedKey(data.google_maps_api_key);
        } else if (!cancelled) {
          setResolvedKey('');
        }
      })
      .catch(() => {
        if (!cancelled) setResolvedKey('');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (resolvedKey === null) return;
    if (window.google?.maps) {
      queueMicrotask(() => setScriptLoaded(true));
      return;
    }
    if (!resolvedKey) {
      queueMicrotask(() => setLoadError(
        'המפתח לא התקבל מהבקאנד. וודא ש-GOOGLE_MAPS_API_KEY מוגדר ב-backend/.env (אותו מפתח שמשמש להמרות כתובות ומסלולים). אין צורך להגדיר מפתח בפרונט – הוא נשלח אוטומטית מ-GET /api/v1/geo/maps-key.'
      ));
      return;
    }
    const existing = document.querySelector('script[src*="maps.googleapis.com"]');
    if (existing) {
      if (window.google?.maps) queueMicrotask(() => setScriptLoaded(true));
      return;
    }
    window.__linkupMapsInit = () => setScriptLoaded(true);
    const script = document.createElement('script');
    script.src = `https://maps.googleapis.com/maps/api/js?key=${resolvedKey}&callback=__linkupMapsInit&loading=async`;
    script.async = true;
    script.defer = true;
    script.onerror = () => setLoadError('טעינת Google Maps נכשלה');
    document.head.appendChild(script);
    return () => {
      delete window.__linkupMapsInit;
    };
  }, [resolvedKey]);

  useEffect(() => {
    if (!scriptLoaded || !data || !window.google?.maps) return;

    const container = containerRef.current;
    if (!container || typeof container !== 'object' || !(container instanceof HTMLElement) || !document.contains(container)) {
      return;
    }

    const origin = coordsToLatLng(data.originCoords);
    const dest = coordsToLatLng(data.destinationCoords);
    const path = pathToLatLngs(data.routeCoords);

    const rafId = requestAnimationFrame(() => {
      const el = containerRef.current;
      if (!el || !document.contains(el)) return;

      const map = new google.maps.Map(el, {
        zoom: 10,
        center: origin,
        mapTypeControl: true,
        fullscreenControl: true,
        zoomControl: true,
      });
      mapRef.current = map;

      if (path.length >= 2) {
        new google.maps.Polyline({
          path,
          geodesic: true,
          strokeColor: '#2563eb',
          strokeOpacity: 1,
          strokeWeight: 4,
          map,
        });
      }

      new google.maps.Marker({
        position: origin,
        map,
        title: 'מוצא',
        label: { text: 'A', color: 'white' },
      });
      new google.maps.Marker({
        position: dest,
        map,
        title: 'יעד',
        label: { text: 'B', color: 'white' },
      });

      const bounds = new google.maps.LatLngBounds();
      bounds.extend(origin);
      bounds.extend(dest);
      path.forEach((p) => bounds.extend(p));
      map.fitBounds(bounds, { top: 50, right: 50, bottom: 50, left: 50 });
    });

    return () => {
      cancelAnimationFrame(rafId);
      mapRef.current = null;
    };
  }, [scriptLoaded, data]);

  if (!data) return null;

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-label="תצוגת מסלול על המפה">
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2 className={styles.title}>תצוגה מקדימה: {data.summary || 'מסלול'}</h2>
          <button
            type="button"
            className={styles.close}
            onClick={onClose}
            aria-label="סגור"
          >
            ×
          </button>
        </div>
        {resolvedKey === null && !loadError && (
          <p className={styles.loading}>טוען מפתח מפה מהבקאנד...</p>
        )}
        {loadError && (
          <p className={styles.error}>{loadError}</p>
        )}
        {!loadError && resolvedKey !== null && (
          <div
            ref={containerRef}
            className={styles.container}
            aria-hidden={!!loadError}
          />
        )}
      </div>
    </div>
  );
}
