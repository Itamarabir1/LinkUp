import { useEffect, useRef } from 'react';

export type LocationCoords = {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
};

interface UseLocationWatcherProps {
  enabled: boolean;
  onPosition: (coords: LocationCoords) => void;
  onError?: (msg: string) => void;
  throttleMs?: number;
}

export function useLocationWatcher({
  enabled,
  onPosition,
  onError,
  throttleMs = 3000,
}: UseLocationWatcherProps) {
  const watchIdRef = useRef<number | null>(null);
  const lastSentRef = useRef<number>(0);
  const onPositionRef = useRef(onPosition);
  const onErrorRef = useRef(onError);
  onPositionRef.current = onPosition;
  onErrorRef.current = onError;

  useEffect(() => {
    if (!enabled) {
      if (watchIdRef.current != null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      lastSentRef.current = 0;
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const now = Date.now();
        if (throttleMs > 0 && now - lastSentRef.current < throttleMs) return;
        lastSentRef.current = now;
        onPositionRef.current({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          heading: pos.coords.heading ?? undefined,
          speed: pos.coords.speed != null ? pos.coords.speed * 3.6 : undefined,
        });
      },
      (err) => onErrorRef.current?.(`שגיאת מיקום: ${err.message || 'גאולוקציה לא זמינה'}`),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
    );

    watchIdRef.current = watchId;
    return () => {
      if (watchIdRef.current != null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [enabled, throttleMs]);
}

