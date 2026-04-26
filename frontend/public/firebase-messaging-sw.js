importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

// Do not hardcode Firebase public config in git-tracked files.
// In containerized runtime, this file is rendered from
// frontend/docker/firebase-messaging-sw.template.js via envsubst.
// This fallback file stays scrubbed to avoid secret-scanner alerts.
firebase.initializeApp({
  apiKey: "",
  authDomain: "",
  projectId: "",
  storageBucket: "",
  messagingSenderId: "",
  appId: "",
});

const messaging = firebase.messaging();

self.addEventListener('push', (event) => {
  const data = event.data?.json()?.data || {};
  const title = data.title || 'LinkUp';
  const body = data.body || '';
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/favicon.png',
      silent: false,
    })
  );
});

messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification || {};
  self.registration.showNotification(title || 'LinkUp', {
    body: body || '',
    icon: '/favicon.png',
    silent: false,
    vibrate: [180, 80, 180],
  });
});
