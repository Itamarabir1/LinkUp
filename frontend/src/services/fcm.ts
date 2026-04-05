import { getToken, onMessage, type MessagePayload } from 'firebase/messaging';
import {
  getMessagingSafe,
  FIREBASE_VAPID_KEY,
} from '../config/firebase';
import { patchFcmToken } from '../api/users';
import { playNotificationChime } from '../utils/notificationSound';
import { triggerNotificationToast } from '../components/NotificationToast/notificationToast.utils';

let foregroundUnsubscribe: (() => void) | null = null;

export function cleanupFCM(): void {
  if (foregroundUnsubscribe) {
    foregroundUnsubscribe();
    foregroundUnsubscribe = null;
  }
}

function showForegroundNotification(payload: MessagePayload): void {
  // Backend sends data-only FCM (title/body in `data` map). SDK may leave `notification` empty.
  const d = payload.data;
  const fromDataTitle = typeof d?.title === 'string' ? d.title.trim() : '';
  const fromDataBody = typeof d?.body === 'string' ? d.body.trim() : '';
  const title =
    fromDataTitle ||
    payload.notification?.title?.trim() ||
    'LinkUp';
  const body =
    fromDataBody || payload.notification?.body?.trim() || '';
  triggerNotificationToast({ title, body });
  playNotificationChime();
}

/**
 * מבקש הרשאת Notifications, רושם את ה-SW, מעביר לו config, מקבל FCM token
 * ושולח ל-backend (PATCH /users/fcm-token).
 * נקרא אוטומטית אחרי התחברות משתמש (AuthContext).
 */
export async function initFCM(): Promise<void> {
  try {
    console.log('[FCM] Starting initFCM...');

    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      console.log('[FCM] Browser not supported');
      return;
    }

    const permission = await Notification.requestPermission();
    console.log('[FCM] Permission:', permission);
    if (permission !== 'granted') return;

    const registration = await navigator.serviceWorker.register(
      '/firebase-messaging-sw.js'
    );
    console.log('[FCM] SW registered:', registration.active?.state);

    // SW config is baked into firebase-messaging-sw.js (no postMessage needed).

    const messaging = getMessagingSafe();
    console.log('[FCM] Messaging instance:', messaging ? 'ok' : 'null');
    if (!messaging) return;

    if (!foregroundUnsubscribe) {
      foregroundUnsubscribe = onMessage(messaging, (payload) => {
        console.log('[FCM] Foreground message received:', payload);
        showForegroundNotification(payload);
      });
      console.log('[FCM] onMessage listener registered');
    }

    const token = await getToken(messaging, {
      vapidKey: FIREBASE_VAPID_KEY,
      serviceWorkerRegistration: registration,
    });
    console.log('[FCM] Token:', token ? token.substring(0, 20) + '...' : 'null');
    if (!token) return;

    await patchFcmToken(token);
    console.log('[FCM] Token sent to backend successfully');
  } catch (err) {
    console.warn('[FCM] init failed:', err);
  }
}
