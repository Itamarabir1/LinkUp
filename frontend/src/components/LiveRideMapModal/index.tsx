import { useEffect, useRef, useState } from 'react';
import { useLocationBroadcast } from '../../hooks/useLocationBroadcast';
import { usePassengerLocations } from '../../hooks/usePassengerLocations';
import { useGoogleMapInstance } from '../../hooks/useGoogleMapInstance';
import { useGoogleMapsKey } from '../../hooks/useGoogleMapsKey';
import { useMapMarker } from '../../hooks/useMapMarker';
import styles from './LiveRideMapModal.module.css';

const DEFAULT_CENTER = { lat: 32.0853, lng: 34.7818 };
const DRIVER_MARKER_BLUE = '#1d6fe8';
const PASSENGER_MARKER_GREEN = '#059669';

type LiveRideMapModalProps = {
  rideId: string;
  driverId: string;
  onClose: () => void;
  /** false = השידור לשרת דרך "שתף מיקום" בהזמנות בלבד; כאן רק תצוגה מקומית */
  broadcastToServer?: boolean;
};

export default function LiveRideMapModal({
  rideId,
  driverId,
  onClose,
  broadcastToServer = true,
}: LiveRideMapModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const passengerMarkersRef = useRef<google.maps.Marker[]>([]);
  const { resolvedKey, loadError: keyError } = useGoogleMapsKey();
  const { map, loadError: mapError } = useGoogleMapInstance(containerRef, resolvedKey);
  const loadError = keyError || mapError;
  const hasInitialPosition = useRef(false);
  const [myPosition, setMyPosition] = useState<{ lat: number; lng: number } | null>(null);

  useLocationBroadcast({
    rideId,
    driverId,
    enabled: broadcastToServer,
  });

  const { locations: passengerLocations, error: passengersError, connected: passengersConnected } = usePassengerLocations(rideId);

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
      (err) => console.error('Geolocation (נהג):', err),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [map]);

  useMapMarker(map, myPosition, { title: 'המיקום שלי (נהג)', color: DRIVER_MARKER_BLUE, scale: 12, strokeWeight: 3 });

  useEffect(() => {
    if (!map || !window.google?.maps) return;

    const passIcon: google.maps.Symbol = {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 10,
      fillColor: PASSENGER_MARKER_GREEN,
      fillOpacity: 1,
      strokeColor: '#ffffff',
      strokeWeight: 2,
    };

    passengerMarkersRef.current.forEach((m) => m.setMap(null));
    passengerMarkersRef.current = passengerLocations.map((loc) => {
      return new google.maps.Marker({
        position: { lat: loc.lat, lng: loc.lng },
        map,
        title: 'נוסע',
        icon: passIcon,
      });
    });

    if (!hasInitialPosition.current && passengerLocations.length > 0) {
      const p = passengerLocations[0];
      map.setCenter({ lat: p.lat, lng: p.lng });
      hasInitialPosition.current = true;
    }
    return () => {
      passengerMarkersRef.current.forEach((m) => m.setMap(null));
      passengerMarkersRef.current = [];
    };
  }, [map, passengerLocations]);

  const statusMsg = passengersError
    ? passengersError
    : passengersConnected
      ? `מחובר לעדכוני נוסעים • ${passengerLocations.length} נוסעים על המפה`
      : 'מתחבר לעדכוני נוסעים...';

  return (
    <div className={styles.backdrop} role="dialog" aria-modal="true" aria-label="מפה חיה - נסיעה פעילה">
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2 className={styles.title}>מפה חיה</h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="סגור">
            ×
          </button>
        </div>
        {resolvedKey === null && !loadError && <p className={styles.statusBar}>טוען מפתח מפה...</p>}
        {loadError && <p className={styles.statusBarError}>{loadError}</p>}
        {!loadError && resolvedKey !== null && (
          <div ref={containerRef} className={styles.mapContainer} aria-hidden={!!loadError} />
        )}
        <div className={passengersError ? styles.statusBarError : styles.statusBar}>{statusMsg}</div>
      </div>
    </div>
  );
}
