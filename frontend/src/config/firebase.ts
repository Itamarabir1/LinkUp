/**
 * Firebase (Web) — אתחול ו-FCM.
 * מפתחות: מקור אמת ב-.env (VITE_FIREBASE_*) — אין ברירות מחדל בקוד.
 */
import { initializeApp } from 'firebase/app';
import { getAnalytics } from 'firebase/analytics';
import { getMessaging } from 'firebase/messaging';

const env = import.meta.env;

/** VAPID key for FCM Web Push (getToken). מ-Firebase Console → Cloud Messaging → Web. */
export const FIREBASE_VAPID_KEY = env.VITE_FIREBASE_VAPID_KEY as string;

const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY,
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: env.VITE_FIREBASE_APP_ID,
  measurementId: env.VITE_FIREBASE_MEASUREMENT_ID,
};

const app = initializeApp(firebaseConfig);

/** Analytics — רק בדפדפן (לא ב-SSR). */
export function getAnalyticsSafe() {
  if (typeof window === 'undefined') return null;
  return getAnalytics(app);
}

/** Messaging (FCM) — רק בדפדפן; לשימוש ב-getToken וכו'. */
export function getMessagingSafe() {
  if (typeof window === 'undefined') return null;
  return getMessaging(app);
}

export { app, firebaseConfig };
