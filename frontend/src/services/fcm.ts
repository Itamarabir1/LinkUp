import { getToken } from 'firebase/messaging';
import {
  getMessagingSafe,
  FIREBASE_VAPID_KEY,
  firebaseConfig,
} from '../config/firebase';
import { api } from '../api/client';

/**
 * מבקש הרשאת Notifications, רושם את ה-SW, מעביר לו config, מקבל FCM token
 * ושולח ל-backend (PATCH /users/fcm-token).
 * נקרא אוטומטית אחרי התחברות משתמש (AuthContext).
 */
export async function initFCM(): Promise<void> {
  try {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) return;

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return;

    const registration = await navigator.serviceWorker.register(
      '/firebase-messaging-sw.js'
    );
    registration.active?.postMessage({
      type: 'FIREBASE_CONFIG',
      config: firebaseConfig,
    });

    const messaging = getMessagingSafe();
    if (!messaging) return;

    const token = await getToken(messaging, {
      vapidKey: FIREBASE_VAPID_KEY,
      serviceWorkerRegistration: registration,
    });
    if (!token) return;

    await api.patch('/users/fcm-token', { fcm_token: token });
  } catch (err) {
    console.warn('FCM init failed:', err);
  }
}
