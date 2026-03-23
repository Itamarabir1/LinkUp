---
name: fcm-foreground-popup
overview: Add foreground FCM handler so system notification pops up when site is open, using FCM payload title/body and permission checks.
todos: []
isProject: false
---

# הוספת פופאפ בזמן Foreground ל-FCM

## מטרה
כשמקבלים FCM בזמן שהאתר פתוח (Foreground), להציג `Notification` של מערכת ההפעלה עם תוכן שמגיע מה־FCM payload (`title`/`body`), ורק אם `Notification.permission === 'granted'`.

## שינוי בקוד
1. עדכון `[frontend/src/services/fcm.ts](frontend/src/services/fcm.ts)`
   - להוסיף מאזין `onMessage(messaging, ...)` בתוך `initFCM()` (חד־פעמי).
   - בתוך ה־handler:
     - בדיקה ש־`Notification.permission === 'granted'`.
     - קריאת תוכן מתוך `payload.notification?.title` ו־`payload.notification?.body` (fallback ל־`LinkUp`/ריק אם חסר).
     - הצגת `new Notification(title, { body, icon: '/favicon.png' })`.
   - להימנע מכפילויות של מאזין ע"י משתנה מודוללי (למשל `let unsubscribe: (()=>void) | null`).

## קבצים שלא משתנים
- אין צורך בשינויים ב־backend.
- אין צורך בשינוי ב־`frontend/public/firebase-messaging-sw.js` כי הוא כבר מטפל ב־Background.

## בדיקות אחרי השינוי
- להיכנס עם משתמש היעד ולוודא `Notifications` = Allow.
- להשאיר את האתר פתוח ב־Foreground.
- לבצע פעולה שמייצרת `PASSENGER_JOIN_REQUEST`.
- לוודא שבזמן שהטאב פתוח קופץ Notification עם הטקסט הנכון (title/body).

## הערת אימות מהיר
- אם עדיין לא רואים פופאפ: לבדוק ב־DevTools שה־`onMessage` אכן מקבל payload, ולהצליב עם logs ב־`/fcm-check`.