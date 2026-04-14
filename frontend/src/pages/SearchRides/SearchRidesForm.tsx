import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { he } from 'date-fns/locale';
import { MapPin, ArrowUpDown, Calendar } from 'lucide-react';
import LoadingButton from '../../components/LoadingButton';
import styles from './SearchRides.module.css';

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

function formatDateDisplay(date: Date): string {
  const now = new Date();
  const tomorrow = new Date();
  tomorrow.setDate(now.getDate() + 1);
  const timeStr = date.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
  if (date.toDateString() === now.toDateString()) return `היום, ${timeStr}`;
  if (date.toDateString() === tomorrow.toDateString()) return `מחר, ${timeStr}`;
  return date.toLocaleDateString('he-IL', { day: 'numeric', month: 'short' }) + `, ${timeStr}`;
}

type Props = {
  error: string;
  pickup: string;
  setPickup: (v: string) => void;
  destination: string;
  setDestination: (v: string) => void;
  searchRadius: number;
  setSearchRadius: (n: number) => void;
  selectedDate: Date;
  setSelectedDate: (d: Date) => void;
  locationLoading: boolean;
  searching: boolean;
  onFillLocation: () => void;
  onSwap: () => void;
  onSubmit: (e: React.FormEvent) => void;
};

export function SearchRidesForm({
  error,
  pickup,
  setPickup,
  destination,
  setDestination,
  searchRadius,
  setSearchRadius,
  selectedDate,
  setSelectedDate,
  locationLoading,
  searching,
  onFillLocation,
  onSwap,
  onSubmit,
}: Props) {
  return (
    <form onSubmit={onSubmit} className={styles.formBlock}>
      {error ? (
        <div className={styles.pageError}>
          {error}
          {error.includes('פג תוקף') && (
            <> · <Link to="/login" className={styles.errorInlineLink}>התחבר מחדש</Link></>
          )}
        </div>
      ) : null}

      {/* Origin + Destination grouped */}
      <div className={styles.routeSection}>
        <div className={styles.fieldRow}>
          <div className={`${styles.fieldIcon} ${styles.origin}`}>
            <MapPin size={15} strokeWidth={2.5} />
          </div>
          <div className={styles.fieldContent}>
            <div className={styles.fieldLabel}>מוצא</div>
            <input
              type="text"
              className={styles.formInput}
              placeholder="כתובת איסוף..."
              value={pickup}
              onChange={(e) => setPickup(e.target.value)}
              autoComplete="off"
            />
          </div>
          <button
            type="button"
            className={styles.gpsBtn}
            onClick={onFillLocation}
            disabled={locationLoading}
            title="מיקום נוכחי"
          >
            {locationLoading ? '...' : 'GPS'}
          </button>
        </div>

        <div className={styles.fieldDivider}>
          <div className={styles.swapWrap}>
            <button
              type="button"
              className={styles.swapBtn}
              onClick={onSwap}
              aria-label="החלף כיוון"
            >
              <ArrowUpDown size={12} strokeWidth={2} />
            </button>
          </div>
        </div>

        <div className={styles.fieldRow}>
          <div className={`${styles.fieldIcon} ${styles.dest}`}>
            <MapPin size={15} strokeWidth={2} />
          </div>
          <div className={styles.fieldContent}>
            <div className={styles.fieldLabel}>יעד</div>
            <input
              type="text"
              className={styles.formInput}
              placeholder="לאן אתה הולך?"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              autoComplete="off"
            />
          </div>
        </div>
      </div>

      {/* Datetime (first in DOM = right in RTL) + radius */}
      <div className={styles.metaRow}>
        <div className={`${styles.metaField} ${styles.metaFieldWide}`}>
          <div className={styles.metaLabel}>תאריך ושעה</div>
          <DatePicker
            selected={selectedDate}
            onChange={(date: Date | null) => date && setSelectedDate(date)}
            showTimeSelect
            timeFormat="HH:mm"
            timeIntervals={15}
            dateFormat="dd/MM/yyyy HH:mm"
            locale={he}
            minDate={new Date()}
            wrapperClassName={styles.datetimeWrapper}
            customInput={<DateTrigger displayText={formatDateDisplay(selectedDate)} />}
          />
        </div>

        <div className={styles.metaField}>
          <div className={styles.metaLabel}>רדיוס חיפוש</div>
          <div className={styles.metaValue}>
            <div className={styles.radiusControl}>
              <button
                type="button"
                className={styles.radiusBtn}
                onClick={() => setSearchRadius(Math.max(1, searchRadius - 1))}
              >−</button>
              <span className={styles.radiusValue}>{searchRadius}</span>
              <button
                type="button"
                className={styles.radiusBtn}
                onClick={() => setSearchRadius(Math.min(50, searchRadius + 1))}
              >+</button>
            </div>
            <span className={styles.radiusUnit}>ק"מ</span>
          </div>
        </div>
      </div>

      <LoadingButton
        type="submit"
        className={styles.searchBtn}
        loading={searching}
        loadingLabel="מחפש..."
      >
        חפש
      </LoadingButton>
    </form>
  );
}
