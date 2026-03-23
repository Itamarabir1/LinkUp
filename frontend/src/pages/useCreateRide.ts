import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAddressFromCoords } from '../api/geo';
import { createRideFromSession, previewRideRoutes } from '../api/rides';
import { useAuth } from '../context/AuthContext';
import type { RidePreviewResponse } from '../types/api';
import { getApiErrorMessage } from '../utils/apiError';
import type { RouteMapData } from '../components/RouteMapModal';

export function useCreateRide() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [originName, setOriginName] = useState('');
  const [destinationName, setDestinationName] = useState('');
  const [selectedDate, setSelectedDate] = useState<Date>(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(9, 0, 0, 0);
    return d;
  });
  const [seats, setSeats] = useState(4);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<RidePreviewResponse | null>(null);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(-1);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [locationLoading, setLocationLoading] = useState(false);
  const [mapPreviewData, setMapPreviewData] = useState<RouteMapData | null>(null);

  const fillOriginFromMyLocation = () => {
    if (!navigator.geolocation) {
      setError('הדפדפן לא תומך במיקום');
      return;
    }
    setLocationLoading(true);
    setError('');
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        try {
          const { data } = await fetchAddressFromCoords(lat, lon);
          setOriginName(data.address ?? '');
        } catch (err) {
          setError(getApiErrorMessage(err, 'לא נמצאה כתובת למיקום זה'));
        } finally {
          setLocationLoading(false);
        }
      },
      () => {
        setError('לא ניתן לקבל מיקום – בדוק הרשאות');
        setLocationLoading(false);
      },
      { timeout: 10000 }
    );
  };

  const handleSwap = () => {
    const o = originName;
    const d = destinationName;
    setOriginName(d);
    setDestinationName(o);
  };

  const requestPreview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!originName.trim() || !destinationName.trim()) {
      setError('נא למלא מוצא ויעד');
      return;
    }
    if (isNaN(selectedDate.getTime()) || selectedDate <= new Date()) {
      setError('נא לבחור זמן יציאה בעתיד');
      return;
    }
    setError('');
    setLoading(true);
    setPreview(null);
    try {
      const { data } = await previewRideRoutes({
        driver_id: Number(user?.user_id) || 0,
        origin_name: originName.trim(),
        destination_name: destinationName.trim(),
        departure_time: selectedDate.toISOString(),
        available_seats: seats,
      });
      const routesList = Array.isArray(data.routes) ? data.routes : (data.routes ? [data.routes] : []);
      setPreview({ ...data, routes: routesList });
      setSelectedRouteIndex(routesList.length === 1 ? 0 : -1);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'תצוגה מקדימה נכשלה'));
    } finally {
      setLoading(false);
    }
  };

  const createRide = async () => {
    if (!preview?.session_id) return;
    const routesCount = preview.routes?.length ?? 0;
    if (routesCount > 1 && (selectedRouteIndex < 0 || selectedRouteIndex >= routesCount)) {
      setError('נא לבחור מסלול');
      return;
    }
    const indexToSend = routesCount === 1 ? 0 : selectedRouteIndex;
    setCreating(true);
    setError('');
    try {
      await createRideFromSession({
        session_id: preview.session_id,
        selected_route_index: indexToSend,
      });
      setPreview(null);
      navigate('/my-rides', { replace: true });
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'יצירת נסיעה נכשלה'));
    } finally {
      setCreating(false);
    }
  };

  return {
    originName,
    setOriginName,
    destinationName,
    setDestinationName,
    selectedDate,
    setSelectedDate,
    seats,
    setSeats,
    loading,
    preview,
    selectedRouteIndex,
    setSelectedRouteIndex,
    creating,
    error,
    locationLoading,
    mapPreviewData,
    setMapPreviewData,
    fillOriginFromMyLocation,
    handleSwap,
    requestPreview,
    createRide,
  };
}
