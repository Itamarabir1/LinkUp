import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { he } from 'date-fns/locale';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { RidePreviewResponse } from '../types/api';
import { formatDurationMinutes } from '../utils/duration';
import { ArrowUpDown } from 'lucide-react';
import RouteMapModal, { type RouteMapData } from '../components/RouteMapModal';
import styles from './CreateRide.module.css';

export default function CreateRide() {
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
  const [seats, setSeats] = useState(4); // ברירת מחדל 4
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<RidePreviewResponse | null>(null);
  /** -1 = לא נבחר (כשיש יותר ממסלול אחד); 0,1,2 = אינדקס המסלול */
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
          const { data } = await api.get<{ address: string }>('/geo/address', {
            params: { lat, lon },
          });
          setOriginName(data.address ?? '');
        } catch {
          setError('לא נמצאה כתובת למיקום זה');
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
      const { data } = await api.post<RidePreviewResponse>(
        '/rides/preview-routes',
        {
          driver_id: user?.user_id ?? 0,
          origin_name: originName.trim(),
          destination_name: destinationName.trim(),
          departure_time: selectedDate.toISOString(),
          available_seats: seats,
        }
      );
      // תמיד להציג את כל המסלולים שהבקאנד מחזיר (גוגל יכולה להחזיר 1–3)
      const routesList = Array.isArray(data.routes) ? data.routes : (data.routes ? [data.routes] : []);
      setPreview({ ...data, routes: routesList });
      // רק אם יש מסלול בודד – נבחר אוטומטית; אחרת המשתמש חייב ללחוץ
      setSelectedRouteIndex(routesList.length === 1 ? 0 : -1);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'תצוגה מקדימה נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
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
      await api.post('/rides/', {
        session_id: preview.session_id,
        selected_route_index: indexToSend,
      });
      setPreview(null);
      navigate('/my-rides', { replace: true });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'יצירת נסיעה נכשלה';
      setError(typeof msg === 'string' ? msg : String(msg));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>הצע נסיעה</h1>
      <p className={styles.pageMeta} style={{ color: '#6b7280', marginBottom: '1rem' }}>
        מוצא, יעד, מושבים וזמן יציאה.
      </p>
      <form onSubmit={requestPreview} className={styles.formBlock}>
        {error && <p className={styles.pageError}>{error}</p>}
        <div className={styles.formRowWithBtn}>
          <input
            type="text"
            placeholder="מוצא (כתובת)"
            value={originName}
            onChange={(e) => setOriginName(e.target.value)}
            className={styles.formInput}
          />
          <button
            type="button"
            className={`${styles.btn} ${styles.btnOutline}`}
            onClick={fillOriginFromMyLocation}
            disabled={locationLoading}
          >
            {locationLoading ? '...' : 'מיקום עצמי'}
          </button>
        </div>
        <div className={styles.swapWrap}>
          <button
            type="button"
            className={styles.swapBtn}
            onClick={handleSwap}
            aria-label="הפוך כיוון"
            title="הפוך כיוון"
          >
            <ArrowUpDown size={18} />
          </button>
        </div>
        <input
          type="text"
          placeholder="יעד (כתובת)"
          value={destinationName}
          onChange={(e) => setDestinationName(e.target.value)}
          className={styles.formInput}
        />
        <label className={styles.formLabel}>מספר מושבים</label>
        <div className={styles.seatsControl}>
          <button
            type="button"
            className={styles.seatBtn}
            onClick={() => setSeats((s) => Math.max(1, s - 1))}
            disabled={seats <= 1}
          >
            −
          </button>
          <span className={styles.seatsValue}>{seats}</span>
          <button
            type="button"
            className={styles.seatBtn}
            onClick={() => setSeats((s) => Math.min(8, s + 1))}
            disabled={seats >= 8}
          >
            +
          </button>
        </div>
        <label className={styles.formLabel}>תאריך ושעת יציאה</label>
        <DatePicker
          selected={selectedDate}
          onChange={(date: Date | null) => date && setSelectedDate(date)}
          showTimeSelect
          timeFormat="HH:mm"
          timeIntervals={15}
          dateFormat="dd/MM/yyyy HH:mm"
          locale={he}
          minDate={new Date()}
          className={styles.datetimeInput}
          placeholderText="בחר תאריך ושעה"
          wrapperClassName={styles.datetimeWrapper}
        />
        <button
          type="submit"
          className={`${styles.btn} ${styles.btnPrimary}`}
          disabled={loading}
        >
          {loading ? 'טוען...' : 'תצוגה מקדימה'}
        </button>
      </form>

      {preview && (preview.routes?.length ?? 0) === 0 && (
        <p className={styles.emptyText} style={{ marginTop: '1rem' }}>לא נמצאו מסלולים. נסה מוצא/יעד אחרים.</p>
      )}
      {preview && (preview.routes?.length ?? 0) > 0 && (
        <div className={styles.previewCard}>
          <h2 className={styles.pageSubtitle}>בחר מסלול</h2>
          <p className={styles.pageMeta} style={{ marginBottom: '1rem' }}>
            גוגל מפות מחזיר עד 3 מסלולים – בחר את המסלול הרצוי.
          </p>
          <div className={styles.routeOptions}>
            {(preview.routes ?? []).map((route) => (
              <div
                key={route.route_index}
                role="button"
                tabIndex={0}
                className={`${styles.card} ${styles.routeOption} ${selectedRouteIndex >= 0 && selectedRouteIndex === route.route_index ? styles.routeOptionSelected : ''}`}
                onClick={() => setSelectedRouteIndex(route.route_index)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedRouteIndex(route.route_index);
                  }
                }}
              >
                <div className={styles.routeOptionContent}>
                  <div className={styles.cardRoute}>
                    מסלול {route.route_index + 1}: {route.summary || '—'}
                  </div>
                  <div className={styles.cardMeta}>
                    {route.distance_km ?? 0} ק"מ · {formatDurationMinutes(route.duration_min ?? 0)}
                  </div>
                </div>
                <button
                  type="button"
                  className={`${styles.btn} ${styles.btnRouteMap}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMapPreviewData({
                      originCoords: preview.origin_coords,
                      destinationCoords: preview.destination_coords,
                      routeCoords: route.coords ?? [],
                      summary: route.summary || '—',
                    });
                  }}
                >
                  תצוגה על המפה
                </button>
              </div>
            ))}
          </div>
          <RouteMapModal data={mapPreviewData} onClose={() => setMapPreviewData(null)} />
          <button
            type="button"
            className={`${styles.btn} ${styles.btnSuccess}`}
            onClick={createRide}
            disabled={creating}
          >
            {creating ? 'יוצר...' : 'צור נסיעה עם המסלול הנבחר'}
          </button>
        </div>
      )}
    </div>
  );
}
