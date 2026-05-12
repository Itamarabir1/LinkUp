importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/11.10.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyA_-AcXKNVAusWm_q2MLq4i70os33FKQdo",
  authDomain: "link-up-d33dc.firebaseapp.com",
  projectId: "link-up-d33dc",
  storageBucket: "link-up-d33dc.firebasestorage.app",
  messagingSenderId: "650241102587",
  appId: "1:650241102587:web:8b81490a43eff80000565e",
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const data = payload.data || {};
  const title = data.title || 'LinkUp';
  const body = data.body || '';
  const options = {
    body,
    icon: '/favicon.png',
    silent: false,
    vibrate: [180, 80, 180],
  };
  if (data.conversation_id) {
    options.tag = 'chat-' + data.conversation_id;
    options.renotify = true;
  }
  self.registration.showNotification(title, options);
});

self.addEventListener('push', (event) => {
  if (event.data) {
    try {
      const payload = event.data.json();
      const data = payload.data || {};
      const title = data.title || 'LinkUp';
      const body = data.body || '';
      const options = {
        body,
        icon: '/favicon.png',
        silent: false,
        vibrate: [180, 80, 180],
      };
      if (data.conversation_id) {
        options.tag = 'chat-' + data.conversation_id;
        options.renotify = true;
      }
      event.waitUntil(
        self.registration.showNotification(title, options)
      );
    } catch (e) {
      const title = event.data.text() || 'LinkUp';
      event.waitUntil(
        self.registration.showNotification(title, {
          icon: '/favicon.png',
        })
      );
    }
  }
});
