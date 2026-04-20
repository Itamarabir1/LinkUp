import { useEffect, useRef, useState } from 'react';
import styles from './PhoneInput.module.css';

interface Country {
  code: string;
  dial: string;
  flag: string;
  namehe: string;
  nameEn: string;
  placeholder: string;
}

const COUNTRIES: Country[] = [
  { code: 'IL', dial: '+972', flag: '🇮🇱', namehe: 'ישראל', nameEn: 'Israel', placeholder: '50 000 0000' },
  { code: 'US', dial: '+1', flag: '🇺🇸', namehe: 'ארה״ב', nameEn: 'United States', placeholder: '555 000 0000' },
  { code: 'GB', dial: '+44', flag: '🇬🇧', namehe: 'בריטניה', nameEn: 'United Kingdom', placeholder: '7700 000000' },
  { code: 'DE', dial: '+49', flag: '🇩🇪', namehe: 'גרמניה', nameEn: 'Germany', placeholder: '151 00000000' },
  { code: 'FR', dial: '+33', flag: '🇫🇷', namehe: 'צרפת', nameEn: 'France', placeholder: '6 00 00 00 00' },
  { code: 'IT', dial: '+39', flag: '🇮🇹', namehe: 'איטליה', nameEn: 'Italy', placeholder: '320 000 0000' },
  { code: 'ES', dial: '+34', flag: '🇪🇸', namehe: 'ספרד', nameEn: 'Spain', placeholder: '612 00 00 00' },
  { code: 'NL', dial: '+31', flag: '🇳🇱', namehe: 'הולנד', nameEn: 'Netherlands', placeholder: '6 00000000' },
  { code: 'CA', dial: '+1', flag: '🇨🇦', namehe: 'קנדה', nameEn: 'Canada', placeholder: '555 000 0000' },
  { code: 'AU', dial: '+61', flag: '🇦🇺', namehe: 'אוסטרליה', nameEn: 'Australia', placeholder: '400 000 000' },
  { code: 'RU', dial: '+7', flag: '🇷🇺', namehe: 'רוסיה', nameEn: 'Russia', placeholder: '912 000 0000' },
  { code: 'TR', dial: '+90', flag: '🇹🇷', namehe: 'טורקיה', nameEn: 'Turkey', placeholder: '532 000 0000' },
  { code: 'UA', dial: '+380', flag: '🇺🇦', namehe: 'אוקראינה', nameEn: 'Ukraine', placeholder: '50 000 0000' },
  { code: 'IN', dial: '+91', flag: '🇮🇳', namehe: 'הודו', nameEn: 'India', placeholder: '98765 43210' },
  { code: 'BR', dial: '+55', flag: '🇧🇷', namehe: 'ברזיל', nameEn: 'Brazil', placeholder: '11 98765 4321' },
];

function parseE164(e164: string): { country: Country; local: string } | null {
  if (!e164) return null;
  const sorted = [...COUNTRIES].sort((a, b) => b.dial.length - a.dial.length);
  for (const c of sorted) {
    if (e164.startsWith(c.dial)) {
      return { country: c, local: e164.slice(c.dial.length) };
    }
  }
  return null;
}

interface PhoneInputProps {
  value: string;
  onChange: (e164: string) => void;
  id?: string;
  error?: boolean;
  defaultCountryCode?: string;
}

export default function PhoneInput({
  value,
  onChange,
  id,
  error,
  defaultCountryCode = 'IL',
}: PhoneInputProps) {
  const defaultCountry = COUNTRIES.find((c) => c.code === defaultCountryCode) ?? COUNTRIES[0];
  const [open, setOpen] = useState(false);
  const [country, setCountry] = useState<Country>(defaultCountry);
  const [localNumber, setLocalNumber] = useState('');
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  // Sync from external value (prefill / reset)
  useEffect(() => {
    if (!value) {
      setLocalNumber('');
      return;
    }
    const parsed = parseE164(value);
    if (parsed) {
      setCountry(parsed.country);
      setLocalNumber(parsed.local);
    }
  }, [value]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => searchRef.current?.focus(), 50);
  }, [open]);

  const isRtl = document.documentElement.dir === 'rtl';

  const filtered = COUNTRIES.filter(
    (c) =>
      c.namehe.includes(search) ||
      c.nameEn.toLowerCase().includes(search.toLowerCase()) ||
      c.dial.includes(search),
  );

  const emitValue = (dial: string, local: string) => {
    if (!local) {
      onChange('');
      return;
    }
    const normalized = local.startsWith('0') ? local.slice(1) : local;
    onChange(`${dial}${normalized}`);
  };

  const selectCountry = (c: Country) => {
    setCountry(c);
    setOpen(false);
    setSearch('');
    emitValue(c.dial, localNumber);
  };

  const handleNumberChange = (raw: string) => {
    const cleaned = raw.replace(/\D/g, '');
    setLocalNumber(cleaned);
    emitValue(country.dial, cleaned);
  };

  return (
    <div className={`${styles.wrapper} ${error ? styles.wrapperError : ''}`} ref={dropdownRef}>
      {/* Country selector */}
      <button
        type="button"
        className={styles.countryBtn}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Select country code"
      >
        <span className={styles.flag}>{country.flag}</span>
        <span className={styles.dial}>{country.dial}</span>
        <svg
          className={`${styles.chevron} ${open ? styles.chevronOpen : ''}`}
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
        >
          <path
            d="M2 4l4 4 4-4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      <div className={styles.divider} />

      {/* Number input */}
      <input
        id={id}
        type="tel"
        inputMode="numeric"
        placeholder={country.placeholder}
        value={localNumber}
        onChange={(e) => handleNumberChange(e.target.value)}
        className={styles.numberInput}
        autoComplete="tel-national"
        maxLength={12}
        dir="ltr"
      />

      {/* Dropdown */}
      {open && (
        <div className={styles.dropdown} role="listbox">
          <div className={styles.searchWrap}>
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={styles.searchIcon}
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <input
              ref={searchRef}
              type="text"
              placeholder="חפש מדינה..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className={styles.searchInput}
            />
          </div>
          <div className={styles.list}>
            {filtered.map((c) => (
              <button
                key={c.code}
                type="button"
                role="option"
                aria-selected={c.code === country.code}
                className={`${styles.option} ${c.code === country.code ? styles.optionActive : ''}`}
                onClick={() => selectCountry(c)}
              >
                <span className={styles.optionFlag}>{c.flag}</span>
                <span className={styles.optionName}>{isRtl ? c.namehe : c.nameEn}</span>
                <span className={styles.optionDial}>{c.dial}</span>
              </button>
            ))}
            {filtered.length === 0 && <p className={styles.noResults}>לא נמצאה מדינה</p>}
          </div>
        </div>
      )}
    </div>
  );
}
