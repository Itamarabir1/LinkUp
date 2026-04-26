import i18n from 'i18next';
import ICU from 'i18next-icu';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import heCommon from './locales/he/common.json';
import heNav from './locales/he/nav.json';
import heAuth from './locales/he/auth.json';
import heRides from './locales/he/rides.json';
import heBookings from './locales/he/bookings.json';
import heGroups from './locales/he/groups.json';
import heProfile from './locales/he/profile.json';
import heBilling from './locales/he/billing.json';

import enCommon from './locales/en/common.json';
import enNav from './locales/en/nav.json';
import enAuth from './locales/en/auth.json';
import enRides from './locales/en/rides.json';
import enBookings from './locales/en/bookings.json';
import enGroups from './locales/en/groups.json';
import enProfile from './locales/en/profile.json';
import enBilling from './locales/en/billing.json';

export type SupportedLang = 'he' | 'en';

i18n
  .use(ICU)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      he: {
        common: heCommon,
        nav: heNav,
        auth: heAuth,
        rides: heRides,
        bookings: heBookings,
        groups: heGroups,
        profile: heProfile,
        billing: heBilling,
      },
      en: {
        common: enCommon,
        nav: enNav,
        auth: enAuth,
        rides: enRides,
        bookings: enBookings,
        groups: enGroups,
        profile: enProfile,
        billing: enBilling,
      },
    },
    lng: 'he',
    fallbackLng: 'he',
    defaultNS: 'common',
    ns: ['common', 'nav', 'auth', 'rides', 'bookings', 'groups', 'profile', 'billing'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'linkup-lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
