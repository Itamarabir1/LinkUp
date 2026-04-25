/**
 * Firebase (Web) — initialization + FCM.
 * Config source: APP_CONFIG.firebase (window.__APP_CONFIG__ at runtime, .env at dev).
 */
import { initializeApp } from 'firebase/app';
import { getAnalytics } from 'firebase/analytics';
import { getMessaging } from 'firebase/messaging';

import { APP_CONFIG } from './runtime';

/** VAPID key for FCM Web Push (getToken), from Firebase Console > Cloud Messaging > Web. */
export const FIREBASE_VAPID_KEY = APP_CONFIG.firebase.vapidKey;

const { vapidKey: _vapidKey, ...firebaseConfig } = APP_CONFIG.firebase;

const app = initializeApp(firebaseConfig);

/** Analytics instance: browser-only (not SSR). */
export function getAnalyticsSafe() {
  if (typeof window === 'undefined') return null;
  return getAnalytics(app);
}

/** Messaging (FCM) instance: browser-only, used by getToken and listeners. */
export function getMessagingSafe() {
  if (typeof window === 'undefined') return null;
  return getMessaging(app);
}

export { app, firebaseConfig };
