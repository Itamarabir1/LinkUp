/* eslint-disable no-restricted-globals */
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

// Config מועבר דינמית מזמן רישום ה-SW (מ-initFCM ב-app)
self.addEventListener('message', (event) => {
  if (event.data?.type === 'FIREBASE_CONFIG') {
    firebase.initializeApp(event.data.config);
    const messaging = firebase.messaging();
    messaging.onBackgroundMessage((payload) => {
      const { title, body } = payload.notification || {};
      self.registration.showNotification(title || 'LinkUp', {
        body: body || '',
        icon: '/favicon.png',
      });
    });
  }
});
