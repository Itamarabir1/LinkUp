import { useCallback, useEffect, useMemo, useState } from 'react';
import { getToken, onMessage } from 'firebase/messaging';
import { patchFcmToken } from '../api/users';
import { FIREBASE_VAPID_KEY, firebaseConfig, getMessagingSafe } from '../config/firebase';
import { initFCM } from '../services/fcm';
import { getApiErrorMessage } from '../utils/apiError';

export type PermissionPillTone = 'ok' | 'warn' | 'bad';

export function useFCMCheck() {
  const [permission, setPermission] = useState<NotificationPermission | 'unsupported'>('default');
  const [swSupported, setSwSupported] = useState(false);
  const [notifSupported, setNotifSupported] = useState(false);
  const [swReady, setSwReady] = useState(false);
  const [lastToken, setLastToken] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<string>('');
  const [lastError, setLastError] = useState<string>('');
  const [busy, setBusy] = useState(false);

  const envOk = useMemo(() => {
    const required = [
      firebaseConfig.apiKey,
      firebaseConfig.authDomain,
      firebaseConfig.projectId,
      firebaseConfig.storageBucket,
      firebaseConfig.messagingSenderId,
      firebaseConfig.appId,
      FIREBASE_VAPID_KEY,
    ];
    return required.every((v) => typeof v === 'string' && v.trim().length > 0);
  }, []);

  const refreshBasics = useCallback(async () => {
    const notifOk = typeof window !== 'undefined' && 'Notification' in window;
    const swOk = typeof navigator !== 'undefined' && 'serviceWorker' in navigator;
    setNotifSupported(notifOk);
    setSwSupported(swOk);
    setPermission(notifOk ? Notification.permission : 'unsupported');

    if (!swOk) {
      setSwReady(false);
      return;
    }
    try {
      const reg = await navigator.serviceWorker.getRegistration('/firebase-messaging-sw.js');
      setSwReady(Boolean(reg));
    } catch {
      setSwReady(false);
    }
  }, []);

  useEffect(() => {
    void refreshBasics();
  }, [refreshBasics]);

  useEffect(() => {
    const messaging = getMessagingSafe();
    if (!messaging) return;
    const unsub = onMessage(messaging, (payload) => {
      setLastMessage(JSON.stringify(payload, null, 2));
    });
    return () => unsub();
  }, []);

  const requestPermission = useCallback(async () => {
    setLastError('');
    if (!('Notification' in window)) {
      setPermission('unsupported');
      return;
    }
    const p = await Notification.requestPermission();
    setPermission(p);
  }, []);

  const registerSwAndSendConfig = useCallback(async () => {
    setLastError('');
    if (!('serviceWorker' in navigator)) return;
    const reg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
    reg.active?.postMessage({ type: 'FIREBASE_CONFIG', config: firebaseConfig });
    setSwReady(true);
  }, []);

  const getTokenOnly = useCallback(async () => {
    setLastError('');
    setBusy(true);
    try {
      const messaging = getMessagingSafe();
      if (!messaging) throw new Error('messaging unavailable (SSR?)');
      if (!('serviceWorker' in navigator)) throw new Error('serviceWorker unsupported');

      const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      registration.active?.postMessage({ type: 'FIREBASE_CONFIG', config: firebaseConfig });

      const token = await getToken(messaging, {
        vapidKey: FIREBASE_VAPID_KEY,
        serviceWorkerRegistration: registration,
      });
      setLastToken(token || null);
    } catch (e) {
      setLastError(getApiErrorMessage(e, e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
      void refreshBasics();
    }
  }, [refreshBasics]);

  const sendTokenToServer = useCallback(async () => {
    setLastError('');
    setBusy(true);
    try {
      if (!lastToken) throw new Error('No token yet. Click "צור Token" קודם.');
      await patchFcmToken(lastToken);
    } catch (e) {
      setLastError(getApiErrorMessage(e, e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }, [lastToken]);

  const runFullInit = useCallback(async () => {
    setLastError('');
    setBusy(true);
    try {
      await initFCM();
    } catch (e) {
      setLastError(getApiErrorMessage(e, e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
      void refreshBasics();
    }
  }, [refreshBasics]);

  const clearLocal = useCallback(async () => {
    setLastError('');
    setLastMessage('');
    setLastToken(null);
    if (!('serviceWorker' in navigator)) return;
    try {
      const reg = await navigator.serviceWorker.getRegistration('/firebase-messaging-sw.js');
      await reg?.unregister();
      setSwReady(false);
    } catch (e) {
      setLastError(String(e));
    }
  }, []);

  const permissionPill = useMemo(() => {
    if (permission === 'unsupported') return { text: 'לא נתמך', tone: 'bad' as const };
    if (permission === 'granted') return { text: 'granted', tone: 'ok' as const };
    if (permission === 'denied') return { text: 'denied', tone: 'bad' as const };
    return { text: 'default', tone: 'warn' as const };
  }, [permission]);

  return {
    envOk,
    notifSupported,
    swSupported,
    swReady,
    lastToken,
    lastMessage,
    lastError,
    busy,
    permissionPill,
    refreshBasics,
    requestPermission,
    registerSwAndSendConfig,
    getTokenOnly,
    sendTokenToServer,
    runFullInit,
    clearLocal,
  };
}
