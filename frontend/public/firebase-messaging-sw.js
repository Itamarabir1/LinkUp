importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyA_-AcXKNVAusWm_q2MLq4i70os33FKQdo",
  authDomain: "link-up-d33dc.firebaseapp.com",
  projectId: "link-up-d33dc",
  storageBucket: "link-up-d33dc.firebasestorage.app",
  messagingSenderId: "650241102587",
  appId: "1:650241102587:web:8b81490a43eff80000565e",
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
