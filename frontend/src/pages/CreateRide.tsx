import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { he } from 'date-fns/locale';
import { formatDurationMinutes } from '../utils/duration';
import { ArrowUpDown } from 'lucide-react';
import ErrorBanner from '../components/ErrorBanner';
import LoadingButton from '../components/LoadingButton';
import RouteMapModal from '../components/RouteMapModal';
import { useCreateRide } from './useCreateRide';
import styles from './CreateRide.module.css';

export default function CreateRide() {
  const {
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
  } = useCreateRide();

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>הצע נסיעה</h1>
      <p className={styles.pageMeta}>מוצא, יעד, מושבים וזמן יציאה.</p>
      <form onSubmit={requestPreview} className={styles.formBlock}>
        {error ? <ErrorBanner message={error} className={styles.pageError} /> : null}
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
        <LoadingButton
          type="submit"
          className={`${styles.btn} ${styles.btnPrimary}`}
          loading={loading}
          loadingLabel="טוען..."
        >
          תצוגה מקדימה
        </LoadingButton>
      </form>

      {preview && (preview.routes?.length ?? 0) === 0 && (
        <p className={styles.routesEmptyHint}>לא נמצאו מסלולים. נסה מוצא/יעד אחרים.</p>
      )}
      {preview && (preview.routes?.length ?? 0) > 0 && (
        <div className={styles.previewCard}>
          <h2 className={styles.pageSubtitle}>בחר מסלול</h2>
          <p className={styles.pageMeta}>גוגל מפות מחזיר עד 3 מסלולים – בחר את המסלול הרצוי.</p>
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
          <LoadingButton
            type="button"
            className={`${styles.btn} ${styles.btnSuccess}`}
            loading={creating}
            loadingLabel="יוצר..."
            onClick={createRide}
          >
            צור נסיעה עם המסלול הנבחר
          </LoadingButton>
        </div>
      )}
    </div>
  );
}
