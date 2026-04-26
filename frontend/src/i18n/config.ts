import i18n from 'i18next';
import ICU from 'i18next-icu';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import heCommon from './locales/he/common.json';
import heNav from './locales/he/nav.json';

import enCommon from './locales/en/common.json';
import enNav from './locales/en/nav.json';

export type SupportedLang = 'he' | 'en';

i18n
  .use(ICU)
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    partialBundledLanguages: true,
    resources: {
      he: {
        common: heCommon,
        nav: heNav,
      },
      en: {
        common: enCommon,
        nav: enNav,
      },
    },
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
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
