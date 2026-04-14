import { useEffect, useRef } from 'react';

export function useMapMarker(
  map: google.maps.Map | null,
  position: { lat: number; lng: number } | null,
  options: {
    title: string;
    color: string;
    isDriver?: boolean;
  }
) {
  const markerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(null);

  useEffect(() => {
    if (!map) return;
    const markerApi = window.google?.maps?.marker;
    if (!markerApi?.AdvancedMarkerElement) return;

    const el = document.createElement('div');

    if (options.isDriver) {
      el.style.cssText = `
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: ${options.color};
        border: 3px solid white;
        box-shadow: 0 2px 12px rgba(0,0,0,0.35);
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      el.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="white">
        <path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/>
      </svg>`;
    } else {
      el.style.cssText = `
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: ${options.color};
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(79,70,229,0.4);
        animation: markerPulse 2s infinite;
      `;
    }

    const marker = new markerApi.AdvancedMarkerElement({
      map: position ? map : null,
      position: position ?? undefined,
      title: options.title,
      content: el,
    });

    markerRef.current = marker;

    return () => {
      if (markerRef.current) {
        markerRef.current.map = null;
        markerRef.current = null;
      }
    };
    // `position` is applied in the next effect so the marker is not recreated on every GPS tick.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, options.isDriver, options.color, options.title]);

  useEffect(() => {
    if (!markerRef.current) return;
    if (position) {
      markerRef.current.position = position;
      markerRef.current.map = map;
    } else {
      markerRef.current.map = null;
    }
  }, [position, map]);
}
