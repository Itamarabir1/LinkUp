/**
 * Runtime config — single source of truth for app-level settings.
 *
 * Production: container entrypoint renders /config.js from a template, populating
 * window.__APP_CONFIG__ with values from environment variables.
 * Dev: window.__APP_CONFIG__ is an empty stub (frontend/public/config.js); values
 * fall back to import.meta.env which Vite hydrates from frontend/.env.
 */

type FirebaseCfg = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
  measurementId: string;
  vapidKey: string;
};

type AppConfig = {
  firebase: FirebaseCfg;
  googleMaps: { apiKey: string; mapId: string };
  google: { clientId: string };
  stripe: { publishableKey: string };
  sentry: { dsn: string; environment: string };
  api: { timeoutMs: number };
};

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<{
      firebase: Partial<FirebaseCfg>;
      googleMaps: Partial<{ apiKey: string; mapId: string }>;
      google: Partial<{ clientId: string }>;
      stripe: Partial<{ publishableKey: string }>;
      sentry: Partial<{ dsn: string; environment: string }>;
      api: Partial<{ timeoutMs: string }>;
    }>;
  }
}

function rt(value: string | undefined): string {
  if (!value) return '';
  if (value.startsWith('${') && value.endsWith('}')) return '';
  return value;
}

function pick(runtime: string | undefined, env: string | undefined, fallback = ''): string {
  return rt(runtime) || env || fallback;
}

const w = typeof window !== 'undefined' ? window.__APP_CONFIG__ ?? {} : {};
const env = import.meta.env;

export const APP_CONFIG: AppConfig = {
  firebase: {
    apiKey: pick(w.firebase?.apiKey, env.VITE_FIREBASE_API_KEY),
    authDomain: pick(w.firebase?.authDomain, env.VITE_FIREBASE_AUTH_DOMAIN),
    projectId: pick(w.firebase?.projectId, env.VITE_FIREBASE_PROJECT_ID),
    storageBucket: pick(w.firebase?.storageBucket, env.VITE_FIREBASE_STORAGE_BUCKET),
    messagingSenderId: pick(w.firebase?.messagingSenderId, env.VITE_FIREBASE_MESSAGING_SENDER_ID),
    appId: pick(w.firebase?.appId, env.VITE_FIREBASE_APP_ID),
    measurementId: pick(w.firebase?.measurementId, env.VITE_FIREBASE_MEASUREMENT_ID),
    vapidKey: pick(w.firebase?.vapidKey, env.VITE_FIREBASE_VAPID_KEY),
  },
  googleMaps: {
    apiKey: pick(w.googleMaps?.apiKey, env.VITE_GOOGLE_MAPS_API_KEY),
    mapId: pick(w.googleMaps?.mapId, env.VITE_GOOGLE_MAPS_MAP_ID, 'linkup_map'),
  },
  google: {
    clientId: pick(w.google?.clientId, env.VITE_GOOGLE_CLIENT_ID),
  },
  stripe: {
    publishableKey: pick(w.stripe?.publishableKey, env.VITE_STRIPE_PUBLISHABLE_KEY),
  },
  sentry: {
    dsn: pick(w.sentry?.dsn, env.VITE_SENTRY_DSN),
    environment: pick(w.sentry?.environment, env.MODE, 'production'),
  },
  api: {
    timeoutMs: Number(pick(w.api?.timeoutMs, env.VITE_API_TIMEOUT_MS)) || 30000,
  },
};
