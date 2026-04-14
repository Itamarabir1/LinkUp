import { createContext, useContext, useLayoutEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import type { SupportedLang } from '../i18n';

type LangContextValue = {
  lang: SupportedLang;
  isRTL: boolean;
  setLang: (nextLang: SupportedLang) => void;
  toggleLang: () => void;
};

const LangContext = createContext<LangContextValue | null>(null);

function normalizeLang(rawLang: string): SupportedLang {
  return rawLang?.startsWith('en') ? 'en' : 'he';
}

function applyLanguageAttrs(lang: SupportedLang) {
  const isRTL = lang === 'he';
  document.documentElement.lang = lang;
  document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
  document.documentElement.style.setProperty('--font-primary', isRTL ? '"Heebo", sans-serif' : '"DM Sans", sans-serif');
}

export function LangProvider({ children }: { children: React.ReactNode }) {
  const { i18n } = useTranslation();
  const lang = normalizeLang(i18n.language);
  const isRTL = lang === 'he';

  useLayoutEffect(() => {
    applyLanguageAttrs(lang);
  }, [lang]);

  const value = useMemo<LangContextValue>(
    () => ({
      lang,
      isRTL,
      setLang: (nextLang) => {
        void i18n.changeLanguage(nextLang);
      },
      toggleLang: () => {
        void i18n.changeLanguage(lang === 'he' ? 'en' : 'he');
      },
    }),
    [i18n, isRTL, lang],
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang() {
  const value = useContext(LangContext);
  if (!value) {
    throw new Error('useLang must be used within LangProvider');
  }
  return value;
}
