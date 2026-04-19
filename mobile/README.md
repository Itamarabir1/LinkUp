# LinkUp – אפליקציית React Native (Expo)

אפליקציית מובייל לחיבור ל-Backend של LinkUp: נהג (הנסיעות שלי, יצירת נסיעה), נוסע (חיפוש, הבקשות שלי), פרופיל ואימות.

## דרישות

- Node.js 18+
- npm או yarn
- Android Studio (לאמולטור אנדרואיד) או מכשיר אנדרואיד
- Backend LinkUp רץ (למשל `http://localhost:8000`)

## התקנה והרצה

```bash
cd mobile
npm install
npm run android
```

להרצה עם iOS (רק על Mac):

```bash
npm run ios
```

## הגדרת כתובת ה-API

ברירת המחדל: `http://10.0.2.2:8000/api/v1` (אמולטור אנדרואיד – localhost של המחשב).

- **מכשיר פיזי:** להגדיר את ה-IP של המחשב ברשת (למשל `192.168.1.10`).
- **קובץ:** `src/config/env.ts` – לערוך `API_BASE_URL` ו-`WS_BASE_URL`, או להגדיר משתני סביבה:
  - `EXPO_PUBLIC_API_URL` – בסיס ל-REST (למשל `https://your-api.com/api/v1`)
  - `EXPO_PUBLIC_WS_URL` – בסיס ל-WebSocket (למשל `wss://your-api.com/api/v1`)

## אבטחה וטוקן

- **Access Token** ו-**Refresh Token** נשמרים ב-**expo-secure-store** (אחסון מאובטח במכשיר).
- כל בקשה מוגנת נשלחת עם `Authorization: Bearer <access_token>`.
- ב-401 מתבצע רענון אוטומטי דרך `POST /auth/refresh`; אם הרענון נכשל – מתנתקים ומנקים אחסון.

## RTL ועברית

- מופעל `I18nManager.forceRTL(true)` בהפעלה.
- טקסטים וכותרות מיושרים לימין (`textAlign: 'right'`).

## מבנה עיקרי

- `src/api/client.ts` – Axios, interceptors, שמירה/מחיקה של טוקנים
- `src/context/AuthContext.tsx` – התחברות, הרשמה, התנתקות, משתמש נוכחי
- `src/screens/` – Login, Register, MyRides, MyRequests, SearchRides, Profile, CreateRide
- `src/navigation/AppNavigator.tsx` – ניווט (Auth stack / Main tabs + CreateRide)
- `src/hooks/useGeo.ts` – "השתמש במיקום שלי" (Expo Location + GET /geo/address)
- `src/config/env.ts` – כתובת API ו-WebSocket

## מפות

- החבילה `react-native-maps` מותקנת. להצגת מפה (מוצא, יעד, מסלול) יש לחבר קומפוננטת Map ולצייר מרקרים ופוליליין מ-`route_coords` / `routes[].coords` מהתצוגה המקדימה.
- מפתח Google Maps: להגדיר ב-`app.json` / `app.config.js` תחת `config.plugins` אם נדרש (Expo Maps).

## CORS

- ב-Backend יש להגדיר ב-`CORS_ORIGINS` או `FRONTEND_URL` את כתובת האפליקציה (למשל `http://localhost:8081` ל-Expo ב-dev).

## הערה על התראות (ווב לעומת מובייל)

באפליקציית ה**ווב** פיד ההתראות הכללי משלב WebSocket ל־`/api/v1/notifications/ws` וגיבוי REST (ראו `ARCHITECTURE.md` / `frontend/docs/ARCHITECTURE.md`). באפליקציית **מובייל** יש לוודא מול הקוד ב־`mobile/src` אילו מסכים נשענים על REST בלבד או על ערוצים נוספים — לא להניח זהות מלאה עם הפרונט בלי בדיקה.
