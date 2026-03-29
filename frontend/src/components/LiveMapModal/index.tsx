import { useEffect, useRef, useState } from 'react';
import { useDriverLocation } from '../../hooks/useDriverLocation';
import { useGoogleMapInstance } from '../../hooks/useGoogleMapInstance';
import { useGoogleMapsKey } from '../../hooks/useGoogleMapsKey';
import { useMapMarker } from '../../hooks/useMapMarker';
import ErrorBanner from '../ErrorBanner';
import styles from './LiveMapModal.module.css';

const DRIVER_BLUE = '#1d6fe8';
const PASSENGER_GREEN = '#059669';

type LiveMapModalProps = {
  bookingId: string;
  onClose: () => void;
};

export default function LiveMapModal({ bookingId, onClose }: LiveMapModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { resolvedKey, loadError: keyError } = useGoogleMapsKey();
  const { map, loadError: mapError } = useGoogleMapInstance(containerRef, resolvedKey);
  const loadError = keyError || mapError;

  const { position: driverPosition, error: driverError, connected } = useDriverLocation(bookingId);
  const hasInitialPosition = useRef(false);
  const [myPosition, setMyPosition] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (!map) return;
    hasInitialPosition.current = false;

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const position = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        setMyPosition(position);
        if (!hasInitialPosition.current) {
          map.setCenter(position);
          hasInitialPosition.current = true;
        }
      },
      (err) => console.error('Geolocation error:', err),
      { enableHighAccuracy: true, maximumAge: 1000, timeout: 10000 }
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, [map]);

  useMapMarker(map, myPosition, { title: 'המיקום שלי', color: PASSENGER_GREEN, scale: 12, strokeWeight: 3 });
  useMapMarker(
    map,
    driverPosition ? { lat: driverPosition.lat, lng: driverPosition.lng } : null,
    { title: 'מיקום הנהג', color: DRIVER_BLUE, scale: 12, strokeWeight: 3 }
  );

  const statusMsg = driverError
    ? driverError
    : connected
      ? driverPosition
        ? 'מקבל עדכוני מיקום מהנהג'
        : 'מחובר – ממתין לעדכון מיקום מהנהג'
      : 'מתחבר...';

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-label="עקוב אחר הנהג">
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2 className={styles.title}>עקוב אחר הנהג</h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="סגור">
            ×
          </button>
        </div>
        {resolvedKey === null && !loadError && <p className={styles.statusBar}>טוען מפתח מפה...</p>}
        {loadError ? (
          <ErrorBanner
            message={loadError}
            variant="compact"
            className={`${styles.statusBar} ${styles.statusBarError}`.trim()}
          />
        ) : null}
        {!loadError && resolvedKey !== null && (
          <div ref={containerRef} className={styles.mapContainer} aria-hidden={!!loadError} />
        )}
        <div className={driverError ? styles.statusBarError : styles.statusBar}>{statusMsg}</div>
      </div>
    </div>
  );
}
