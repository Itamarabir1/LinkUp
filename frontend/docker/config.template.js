window.__APP_CONFIG__ = Object.freeze({
  firebase: {
    apiKey: "${VITE_FIREBASE_API_KEY}",
    authDomain: "${VITE_FIREBASE_AUTH_DOMAIN}",
    projectId: "${VITE_FIREBASE_PROJECT_ID}",
    storageBucket: "${VITE_FIREBASE_STORAGE_BUCKET}",
    messagingSenderId: "${VITE_FIREBASE_MESSAGING_SENDER_ID}",
    appId: "${VITE_FIREBASE_APP_ID}",
    measurementId: "${VITE_FIREBASE_MEASUREMENT_ID}",
    vapidKey: "${VITE_FIREBASE_VAPID_KEY}",
  },
  googleMaps: {
    apiKey: "${VITE_GOOGLE_MAPS_API_KEY}",
    mapId: "${VITE_GOOGLE_MAPS_MAP_ID}",
  },
  google: {
    clientId: "${VITE_GOOGLE_CLIENT_ID}",
  },
  stripe: {
    publishableKey: "${VITE_STRIPE_PUBLISHABLE_KEY}",
  },
  sentry: {
    dsn: "${VITE_SENTRY_DSN}",
    environment: "${APP_ENV}",
  },
  api: {
    timeoutMs: "${VITE_API_TIMEOUT_MS}",
  },
});
