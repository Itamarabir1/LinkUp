import { useEffect, useRef } from 'react';

export function useMapMarker(
  map: google.maps.Map | null,
  position: { lat: number; lng: number } | null,
  options: {
    title: string;
    color: string;
    scale?: number;
    strokeWeight?: number;
  }
) {
  const markerRef = useRef<google.maps.Marker | null>(null);

  // יצירה חד-פעמית — רק כש-map או אופציות משתנים
  useEffect(() => {
    if (!map || !window.google?.maps) return;

    const marker = new window.google.maps.Marker({
      map,
      title: options.title,
      icon: {
        path: window.google.maps.SymbolPath.CIRCLE,
        scale: options.scale ?? 12,
        fillColor: options.color,
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: options.strokeWeight ?? 3,
      },
    });
    marker.setVisible(false);
    markerRef.current = marker;

    return () => {
      markerRef.current?.setMap(null);
      markerRef.current = null;
    };
  }, [map, options.title, options.color, options.scale, options.strokeWeight]);

  // עדכון מיקום בלבד — ללא יצירה מחדש
  useEffect(() => {
    if (!markerRef.current) return;
    if (position) {
      markerRef.current.setPosition(position);
      markerRef.current.setVisible(true);
    } else {
      markerRef.current.setVisible(false);
    }
  }, [position]);
}
