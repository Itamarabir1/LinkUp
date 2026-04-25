import './i18n';
import * as Sentry from '@sentry/react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.tsx';
import { APP_CONFIG } from './config/runtime';
import { getAnalyticsSafe } from './config/firebase';

getAnalyticsSafe();

if (import.meta.env.PROD && APP_CONFIG.sentry.dsn) {
  Sentry.init({
    dsn: APP_CONFIG.sentry.dsn,
    environment: APP_CONFIG.sentry.environment,
    tracesSampleRate: 0.1,
  });
}

createRoot(document.getElementById('root')!).render(<App />);