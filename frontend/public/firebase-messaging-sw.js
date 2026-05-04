importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-messaging-compat.js');

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

messaging.onBackgroundMessage((payload) => {
  const data = payload.data || {};
  const title = data.title || 'LinkUp';
  const body = data.body || '';
  self.registration.showNotification(title, {
    body,
    icon: '/favicon.png',
    silent: false,
    vibrate: [180, 80, 180],
  });
});
