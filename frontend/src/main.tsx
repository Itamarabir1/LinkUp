import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { getAnalyticsSafe } from './config/firebase'

getAnalyticsSafe()

// TODO: Sentry — להסיר הערה כשעוברים לפרודקשן ומוסיפים VITE_SENTRY_DSN ל-.env
// import * as Sentry from "@sentry/react";
// if (import.meta.env.PROD && import.meta.env.VITE_SENTRY_DSN) {
//   Sentry.init({
//     dsn: import.meta.env.VITE_SENTRY_DSN,
//     environment: "production",
//     tracesSampleRate: 0.1,
//   });
// }

createRoot(document.getElementById('root')!).render(<App />)