import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { enUS, he } from 'date-fns/locale';
import { useTranslation } from 'react-i18next';
import { MapPin, ArrowUpDown, Calendar } from 'lucide-react';
import LoadingButton from '../../components/LoadingButton';
import { useLang } from '../../context/LangContext';
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

function formatDateDisplay(date: Date, lang: 'he' | 'en', todayLabel: string, tomorrowLabel: string): string {
  const locale = lang === 'en' ? 'en-US' : 'he-IL';
  const now = new Date();
  const tomorrow = new Date();
  tomorrow.setDate(now.getDate() + 1);
  const timeStr = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  if (date.toDateString() === now.toDateString()) return `${todayLabel}, ${timeStr}`;
  if (date.toDateString() === tomorrow.toDateString()) return `${tomorrowLabel}, ${timeStr}`;
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short' }) + `, ${timeStr}`;
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
  const { t } = useTranslation(['rides', 'common', 'auth']);
  const { lang } = useLang();
  return (
    <form onSubmit={onSubmit} className={styles.formBlock}>
      {error ? (
        <div className={styles.pageError}>
          {error}
          {error.includes('פג תוקף') && (
            <> · <Link to="/login" className={styles.errorInlineLink}>{t('auth:signIn')}</Link></>
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
            <div className={styles.fieldLabel}>{t('rides:origin')}</div>
            <input
              type="text"
              className={styles.formInput}
              placeholder={t('rides:originPlaceholder')}
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
            title={t('rides:myLocation')}
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
              aria-label={t('rides:swapDirection')}
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
            <div className={styles.fieldLabel}>{t('rides:destination')}</div>
            <input
              type="text"
              className={styles.formInput}
              placeholder={t('rides:destinationPlaceholder')}
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
          <div className={styles.metaLabel}>{t('rides:departureTime')}</div>
          <DatePicker
            selected={selectedDate}
            onChange={(date: Date | null) => date && setSelectedDate(date)}
            showTimeSelect
            timeFormat="HH:mm"
            timeIntervals={15}
            dateFormat="dd/MM/yyyy HH:mm"
            locale={lang === 'en' ? enUS : he}
            minDate={new Date()}
            wrapperClassName={styles.datetimeWrapper}
            customInput={<DateTrigger displayText={formatDateDisplay(selectedDate, lang, t('common:today'), t('common:tomorrow'))} />}
          />
        </div>

        <div className={styles.metaField}>
          <div className={styles.metaLabel}>{t('rides:searchRadius')}</div>
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
            <span className={styles.radiusUnit}>{t('rides:km')}</span>
          </div>
        </div>
      </div>

      <LoadingButton
        type="submit"
        className={styles.searchBtn}
        loading={searching}
        loadingLabel={t('rides:searching')}
      >
        {t('common:search')}
      </LoadingButton>
    </form>
  );
}
