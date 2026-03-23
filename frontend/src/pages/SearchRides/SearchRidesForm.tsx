import { Link } from 'react-router-dom';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { he } from 'date-fns/locale';
import { ArrowUpDown } from 'lucide-react';
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
      <div className={styles.formRowWithBtn}>
        <input
          type="text"
          placeholder="מוצא (כתובת איסוף)"
          value={pickup}
          onChange={(e) => setPickup(e.target.value)}
          className={styles.formInput}
        />
        <button
          type="button"
          className={`${styles.btn} ${styles.btnOutline}`}
          onClick={onFillLocation}
          disabled={locationLoading}
        >
          {locationLoading ? '...' : 'מיקום עצמי'}
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
      <label className={styles.formLabel}>רדיוס חיפוש (מטרים)</label>
      <input
        type="number"
        min={100}
        value={searchRadius}
        onChange={(e) => setSearchRadius(parseInt(e.target.value, 10) || 1000)}
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
