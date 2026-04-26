import './i18n';
import * as Sentry from '@sentry/react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';
import { APP_CONFIG } from './config/runtime';
import { getAnalyticsSafe } from './config/firebase';

getAnalyticsSafe();

if (import.meta.env.DEV) {
  import('@axe-core/react').then(({ default: axe }) => {
    import('react').then(({ default: React }) => {
      import('react-dom').then(({ default: ReactDOM }) => {
        void axe(React, ReactDOM, 1000);
      });
    });
  });
}

if (import.meta.env.PROD && APP_CONFIG.sentry.dsn) {
  const sentryWithMetrics = Sentry as unknown as {
    metrics?: {
      distribution: (name: string, value: number, options?: { unit?: string }) => void;
    };
  };

  Sentry.init({
    dsn: APP_CONFIG.sentry.dsn,
    environment: APP_CONFIG.sentry.environment,
    tracesSampleRate: 0.1,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    replaysSessionSampleRate: 0.05,
    replaysOnErrorSampleRate: 1.0,
  });

  import('web-vitals').then(({ onCLS, onINP, onLCP }) => {
    onCLS((m) => sentryWithMetrics.metrics?.distribution('web_vitals.cls', m.value, { unit: 'none' }));
    onLCP((m) => sentryWithMetrics.metrics?.distribution('web_vitals.lcp', m.value, { unit: 'millisecond' }));
    onINP((m) => sentryWithMetrics.metrics?.distribution('web_vitals.inp', m.value, { unit: 'millisecond' }));
  });
}

createRoot(document.getElementById('root')!).render(<App />);