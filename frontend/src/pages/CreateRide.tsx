import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { he } from 'date-fns/locale';
import { forwardRef } from 'react';
import { formatDurationMinutes } from '../utils/duration';
import { MapPin, ArrowUpDown, ChevronRight, Map, Calendar } from 'lucide-react';
import LoadingButton from '../components/LoadingButton';
import RouteMapModal from '../components/RouteMapModal';
import { useGroup } from '../context/GroupContext';
import { useCreateRide } from './useCreateRide';
import styles from './CreateRide.module.css';

interface DateTriggerProps {
  value?: string;
  onClick?: () => void;
  displayText: string;
}

const DateTrigger = forwardRef<HTMLButtonElement, DateTriggerProps>(
  ({ onClick, displayText }, ref) => (
    <button
      type="button"
      ref={ref}
      onClick={onClick}
      className={styles.datetimeTrigger}
      aria-label={`שנה תאריך ושעה: ${displayText}`}
    >
      <Calendar size={14} strokeWidth={2} className={styles.datetimeIcon} />
      <span>{displayText}</span>
    </button>
  )
);

function StepIndicator({ step }: { step: 1 | 2 }) {
  return (
    <div className={styles.stepsRow}>
      <div className={styles.stepItem}>
        <div className={`${styles.stepCircle} ${step === 1 ? styles.active : styles.done}`}>
          {step === 1 ? '1' : '✓'}
        </div>
        <span className={`${styles.stepLabel} ${step === 1 ? styles.active : styles.idle}`}>
          פרטי הנסיעה
        </span>
      </div>
      <div className={`${styles.stepLine} ${step === 2 ? styles.done : ''}`} />
      <div className={styles.stepItem}>
        <div className={`${styles.stepCircle} ${step === 2 ? styles.active : styles.idle}`}>
          2
        </div>
        <span className={`${styles.stepLabel} ${step === 2 ? styles.active : styles.idle}`}>
          בחר מסלול
        </span>
      </div>
    </div>
  );
}

export default function CreateRide() {
  const { myGroups } = useGroup();
  const {
    groupId, originName, setOriginName, destinationName, setDestinationName,
    selectedDate, setSelectedDate, seats, setSeats, loading, preview,
    selectedRouteIndex, setSelectedRouteIndex, creating, error, locationLoading,
    mapPreviewData, setMapPreviewData, fillOriginFromMyLocation, handleSwap,
    requestPreview, createRide,
  } = useCreateRide();

  const activeGroupName = groupId
    ? myGroups.find((g) => g.group_id === groupId)?.name
    : null;

  const hasPreview = preview && (preview.routes?.length ?? 0) > 0;
  const currentStep: 1 | 2 = hasPreview ? 2 : 1;

  const formatDateDisplay = (date: Date) => {
    const now = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(now.getDate() + 1);
    const timeStr = date.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
    if (date.toDateString() === now.toDateString()) return `היום, ${timeStr}`;
    if (date.toDateString() === tomorrow.toDateString()) return `מחר, ${timeStr}`;
    return date.toLocaleDateString('he-IL', { day: 'numeric', month: 'short' }) + `, ${timeStr}`;
  };

  return (
    <div className={styles.page}>
      <a href={groupId ? `/groups/${groupId}` : '/my-rides'} className={styles.backLink}>
        <ChevronRight size={14} />
        {groupId ? 'חזור לקבוצה' : 'הנסיעות שלי'}
      </a>

      <StepIndicator step={currentStep} />

      {!hasPreview && (
        <>
          <div className={styles.pageHeader}>
            {activeGroupName && (
              <div className={styles.groupPill}>
                <span className={styles.groupPillDot} />
                נוסע בשם קבוצה: {activeGroupName}
              </div>
            )}
            <h1 className={styles.pageTitle}>לאן אתה נוסע?</h1>
            <p className={styles.pageMeta}>
              הזן מסלול, מספר מושבים ושעת יציאה — ונמצא את הנתיב הטוב ביותר
            </p>
          </div>

          <form onSubmit={requestPreview}>
            {error ? <div className={styles.pageError}>{error}</div> : null}

            <div className={styles.formBlock}>
              <div className={styles.routeSection}>
                <div className={styles.fieldRow}>
                  <div className={`${styles.fieldIcon} ${styles.origin}`}>
                    <MapPin size={15} strokeWidth={2.5} />
                  </div>
                  <div className={styles.fieldContent}>
                    <div className={styles.fieldLabel}>מוצא</div>
                    <input type="text" className={styles.formInput} placeholder="כתובת איסוף..."
                      value={originName} onChange={(e) => setOriginName(e.target.value)} autoComplete="off" />
                  </div>
                  <button type="button" className={styles.gpsBtn}
                    onClick={fillOriginFromMyLocation} disabled={locationLoading} title="מיקום נוכחי">
                    {locationLoading ? '...' : 'GPS'}
                  </button>
                </div>

                <div className={styles.fieldDivider}>
                  <div className={styles.swapWrap}>
                    <button type="button" className={styles.swapBtn} onClick={handleSwap} aria-label="החלף כיוון">
                      <ArrowUpDown size={13} strokeWidth={2} />
                    </button>
                  </div>
                </div>

                <div className={styles.fieldRow}>
                  <div className={`${styles.fieldIcon} ${styles.dest}`}>
                    <MapPin size={15} strokeWidth={2} />
                  </div>
                  <div className={styles.fieldContent}>
                    <div className={styles.fieldLabel}>יעד</div>
                    <input type="text" className={styles.formInput} placeholder="לאן אתה הולך?"
                      value={destinationName} onChange={(e) => setDestinationName(e.target.value)} autoComplete="off" />
                  </div>
                </div>
              </div>

              <div className={styles.metaRow}>
                <div className={styles.metaField}>
                  <div className={styles.metaLabel}>מושבים פנויים</div>
                  <div className={styles.metaValue}>
                    <div className={styles.seatsControl}>
                      <button type="button" className={styles.seatBtn}
                        onClick={() => setSeats((s) => Math.max(1, s - 1))} disabled={seats <= 1}>−</button>
                      <span className={styles.seatsValue}>{seats}</span>
                      <button type="button" className={styles.seatBtn}
                        onClick={() => setSeats((s) => Math.min(8, s + 1))} disabled={seats >= 8}>+</button>
                    </div>
                    <span className={styles.seatsUnit}>נוסעים</span>
                  </div>
                </div>

                <div className={styles.metaField}>
                  <div className={styles.metaLabel}>תאריך ושעה</div>
                  <DatePicker
                    selected={selectedDate}
                    onChange={(date: Date | null) => date && setSelectedDate(date)}
                    showTimeSelect timeFormat="HH:mm" timeIntervals={15}
                    dateFormat="dd/MM/yyyy HH:mm" locale={he} minDate={new Date()}
                    wrapperClassName={styles.datetimeWrapper}
                    customInput={<DateTrigger displayText={formatDateDisplay(selectedDate)} />}
                  />
                </div>
              </div>

              <LoadingButton type="submit" className={`${styles.btn} ${styles.btnPrimary}`}
                loading={loading} loadingLabel="מחשב מסלולים...">
                תצוגה מקדימה
              </LoadingButton>
            </div>
          </form>
        </>
      )}

      {preview && (preview.routes?.length ?? 0) === 0 && (
        <p className={styles.routesEmptyHint}>לא נמצאו מסלולים. נסה מוצא/יעד אחרים.</p>
      )}

      {hasPreview && (
        <>
          <div className={styles.pageHeader}>
            <h1 className={styles.pageTitle}>בחר מסלול</h1>
            <p className={styles.pageMeta}>נמצאו {preview.routes!.length} מסלולים — בחר את הנתיב המועדף עליך</p>
          </div>

          {error ? <div className={styles.pageError}>{error}</div> : null}

          <div className={styles.sectionLabel}>מסלולים זמינים</div>

          <div className={styles.routeOptions}>
            {preview.routes!.map((route, idx) => (
              <div key={route.route_index} role="button" tabIndex={0}
                className={`${styles.routeOption} ${selectedRouteIndex === route.route_index ? styles.routeOptionSelected : ''}`}
                onClick={() => setSelectedRouteIndex(route.route_index)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedRouteIndex(route.route_index); } }}>
                <div className={styles.routeOptionContent}>
                  <div className={styles.cardRoute}>
                    מסלול {route.route_index + 1}{route.summary ? ` — ${route.summary}` : ''}
                  </div>
                  <div className={styles.cardMeta}>
                    <span>{route.distance_km ?? 0} ק"מ</span>
                    <span className={styles.routeMetaDot} />
                    <span>{formatDurationMinutes(route.duration_min ?? 0)}</span>
                    {idx === 0 && (<><span className={styles.routeMetaDot} /><span className={styles.routeFastest}>מהיר ביותר</span></>)}
                  </div>
                </div>
                <button type="button" className={styles.btnRouteMap}
                  onClick={(e) => { e.stopPropagation(); setMapPreviewData({ originCoords: preview.origin_coords, destinationCoords: preview.destination_coords, routeCoords: route.coords ?? [], summary: route.summary || '' }); }}>
                  <Map size={12} style={{ display: 'inline', marginLeft: 4 }} />מפה
                </button>
                <div className={styles.routeSelIndicator}>
                  {selectedRouteIndex === route.route_index && (
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#fff' }} />
                  )}
                </div>
              </div>
            ))}
          </div>

          <p className={styles.routeHint}>לחץ על מסלול לבחירה · לחץ "מפה" לצפייה בנתיב</p>

          <RouteMapModal data={mapPreviewData} onClose={() => setMapPreviewData(null)} />

          <LoadingButton type="button" className={`${styles.btn} ${styles.btnSuccess}`}
            loading={creating} loadingLabel="יוצר נסיעה..." onClick={createRide}>
            צור נסיעה עם המסלול הנבחר
          </LoadingButton>
        </>
      )}
    </div>
  );
}
