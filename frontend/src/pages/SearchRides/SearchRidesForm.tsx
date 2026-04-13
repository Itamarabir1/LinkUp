import { Link } from 'react-router-dom';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { he } from 'date-fns/locale';
import { MapPin, ArrowUpDown } from 'lucide-react';
import ErrorBanner from '../../components/ErrorBanner';
import styles from './SearchRides.module.css';

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
        <ErrorBanner message={error} className={styles.pageError}>
          {error.includes('פג תוקף') ? (
            <>
              {' '}
              <Link to="/login" className={styles.errorInlineLink}>
                התחבר מחדש
              </Link>
            </>
          ) : null}
        </ErrorBanner>
      ) : null}
      <div style={{ position: 'relative' }}>
        <input
          type="text"
          placeholder="מוצא (כתובת איסוף)"
          value={pickup}
          onChange={(e) => setPickup(e.target.value)}
          className={styles.formInput}
          style={{ paddingLeft: '2.5rem' }}
        />
        <button
          type="button"
          onClick={onFillLocation}
          disabled={locationLoading}
          title="מיקום עצמי"
          style={{
            position: 'absolute',
            left: '0.75rem',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--primary)',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {locationLoading
            ? <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>...</span>
            : <MapPin size={18} strokeWidth={2} />
          }
        </button>
      </div>
      <div className={styles.swapWrap}>
        <button
          type="button"
          className={styles.swapBtn}
          onClick={onSwap}
          aria-label="הפוך כיוון"
          title="הפוך כיוון"
        >
          <ArrowUpDown size={18} />
        </button>
      </div>
      <input
        type="text"
        placeholder="יעד (כתובת)"
        value={destination}
        onChange={(e) => setDestination(e.target.value)}
        className={styles.formInput}
      />
      <label className={styles.formLabel}>רדיוס חיפוש (ק"מ)</label>
      <input
        type="number"
        min={0.1}
        max={50}
        step={0.1}
        value={searchRadius}
        onChange={(e) => setSearchRadius(parseFloat(e.target.value) || 1)}
        className={styles.formInput}
      />
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
      <button type="submit" className={`${styles.btn} ${styles.btnSuccess}`} disabled={searching}>
        {searching ? 'מחפש...' : 'חפש'}
      </button>
    </form>
  );
}
