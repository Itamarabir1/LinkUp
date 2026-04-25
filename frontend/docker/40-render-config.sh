#!/bin/sh
set -e

VARS='${VITE_FIREBASE_API_KEY} ${VITE_FIREBASE_AUTH_DOMAIN} ${VITE_FIREBASE_PROJECT_ID} ${VITE_FIREBASE_STORAGE_BUCKET} ${VITE_FIREBASE_MESSAGING_SENDER_ID} ${VITE_FIREBASE_APP_ID} ${VITE_FIREBASE_MEASUREMENT_ID} ${VITE_FIREBASE_VAPID_KEY} ${VITE_GOOGLE_MAPS_API_KEY} ${VITE_GOOGLE_MAPS_MAP_ID} ${VITE_GOOGLE_CLIENT_ID} ${VITE_STRIPE_PUBLISHABLE_KEY} ${VITE_SENTRY_DSN} ${VITE_API_TIMEOUT_MS} ${APP_ENV}'

envsubst "$VARS" < /etc/linkup/config.template.js > /usr/share/nginx/html/config.js
envsubst "$VARS" < /etc/linkup/firebase-messaging-sw.template.js > /usr/share/nginx/html/firebase-messaging-sw.js
