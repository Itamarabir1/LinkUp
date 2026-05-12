import { getToken, onMessage, type MessagePayload } from 'firebase/messaging';
import {
  getMessagingSafe,
  FIREBASE_VAPID_KEY,
} from '../config/firebase';
import { patchFcmToken } from '../api/users';
import { playNotificationChime } from '../utils/notificationSound';
import { triggerNotificationToast } from '../components/NotificationToast/notificationToast.utils';

const FCM_TOKEN_STORAGE_KEY = 'fcm_token';

function devLog(...args: unknown[]): void {
  if (import.meta.env.DEV) {
    console.log(...args);
  }
}

let foregroundUnsubscribe: (() => void) | null = null;

export function cleanupFCM(): void {
  if (foregroundUnsubscribe) {
    foregroundUnsubscribe();
    foregroundUnsubscribe = null;
  }
  localStorage.removeItem(FCM_TOKEN_STORAGE_KEY);
}

function showForegroundNotification(payload: MessagePayload): void {
  if (payload.data?.event_key === 'chat.message_sent') return;
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
 * Requests notification permission, registers the SW, obtains an FCM token,
 * and sends it to the backend (PATCH /users/fcm-token).
 * Called automatically after user login (AuthContext).
 */
export async function initFCM(): Promise<void> {
  try {
    devLog('[FCM] Starting initFCM...');

    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      devLog('[FCM] Browser not supported');
      return;
    }

    const permission = await Notification.requestPermission();
    devLog('[FCM] Permission:', permission);
    if (permission !== 'granted') return;

    const registration = await navigator.serviceWorker.register(
      '/firebase-messaging-sw.js'
    );
    devLog('[FCM] SW registered:', registration.active?.state);

    // SW config is baked into firebase-messaging-sw.js (no postMessage needed).

    const messaging = getMessagingSafe();
    devLog('[FCM] Messaging instance:', messaging ? 'ok' : 'null');
    if (!messaging) return;

    if (!foregroundUnsubscribe) {
      foregroundUnsubscribe = onMessage(messaging, (payload) => {
        devLog('[FCM] Foreground message received:', payload);
        showForegroundNotification(payload);
      });
      devLog('[FCM] onMessage listener registered');
    }

    const token = await getToken(messaging, {
      vapidKey: FIREBASE_VAPID_KEY,
      serviceWorkerRegistration: registration,
    });
    devLog('[FCM] Token:', token ? token.substring(0, 20) + '...' : 'null');
    if (!token) return;

    const cachedToken = localStorage.getItem(FCM_TOKEN_STORAGE_KEY);
    if (token !== cachedToken) {
      await patchFcmToken(token);
      localStorage.setItem(FCM_TOKEN_STORAGE_KEY, token);
      devLog('[FCM] Token sent to backend successfully');
    } else {
      devLog('[FCM] Token unchanged, skipping backend update');
    }
  } catch (err) {
    console.warn('[FCM] init failed:', err);
  }
}
