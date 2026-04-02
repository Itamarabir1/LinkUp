# Linkup Frontend (React + Vite)

אפליקציית ווב ב-React + TypeScript (Vite) ל-Linkup: ניהול נסיעות, קבוצות, צ'אט בזמן אמת, התחברות עם Google ואימייל/סיסמה, תמונות פרופיל (S3) ותמיכה מלאה ב-RTL בעברית.

> **הערה:** ריצת Frontend CI ב-GitHub מופעלת רק כשקומיט משנה קבצים תחת `frontend/`.

---

## דרישות

- Node.js 18+
- npm (או pnpm / yarn אם מעדיפים)
- Backend רץ (ברירת מחדל: `http://127.0.0.1:8000`)


---

## התקנה והרצה בפיתוח

```bash
cd frontend
npm install
npm run dev
```

ברירת המחדל של Vite היא `http://localhost:5173`.  
הבקשות ל-API עוברות דרך proxy של Vite אל ה-backend (ללא בעיות CORS) כאשר עובדים ב-dev.

---

## משתני סביבה (`frontend/.env`)

יש קובץ `frontend/.env.example` עם ברירות מחדל. כדי להתחיל:

```bash
cp frontend/.env.example frontend/.env
# ערוך את frontend/.env לפי הצורך
```

המשתנים העיקריים:

- **REST API** – תמיד נתיב יחסי `/api/v1` (אותו host; Vite proxy בפיתוח ל־`localhost:8000`, Nginx בפרודקשן).
- **צ'אט WebSocket** – ב־[`src/config/env.ts`](src/config/env.ts) פונקציה `getChatWebSocketUrl`: ב־**DEV** (`import.meta.env.DEV`) חיבור **ישיר** ל־`ws://localhost:8081/ws?token=…` (שירות `chat-ws` בדוקר מפרסם 8081 ל־host). ב־**production** — `ws:` / `wss:` לפי הדף, עם `window.location.host` ונתיב `/ws`. אין משתנה `VITE_CHAT_WS_URL`. ב־Vite מוגדר גם proxy ל־`/ws` → 8081 (שימושי אם קוד אחר פונה לנתיב יחסי).
- **WebSocket נסיעות / התראות (Backend)** – `getWsBaseUrl()` ב־**DEV**: `ws://localhost:8000/api/v1`; בפרודקשן: אותו host + `/api/v1`.
- **Presence HTTP** – `GET /presence/...` דרך `chatWsApi`: ב־dev ה־Vite מפרוקסי `/presence` ל־`localhost:8081` (ראו `vite.config.ts`), בפרודקשן — דרך Nginx לאותו origin.
- `VITE_API_TIMEOUT_MS` – timeout לבקשות HTTP במילישניות (ברירת מחדל: `30000`).
- `VITE_GOOGLE_MAPS_API_KEY` – מפתח Google Maps להצגת מפה ונתיב נסיעה (אופציונלי; חלק מהמסכים עובדים גם בלעדיו).
- `VITE_GOOGLE_CLIENT_ID` – Client ID של Google OAuth (חובה לכניסה עם Google, בשימוש ב-`GoogleSignIn`).

הקובץ `src/config/env.ts` מרכז את הקריאה למשתנים האלה ומספק fallback הגיוני לסביבת פיתוח.

---

## סקריפטים שימושיים

- `npm run dev` – הרצה חיה עם HMR ב-`http://localhost:5173`.
- `npm run build` – בניית production ל-`dist/`.
- `npm run preview` – הרצת build מקומי לבדיקה.
- `npm run lint` – הרצת ESLint על TypeScript/React.

---

## נקודות מפתח בפרונטנד

- **RTL ועברית** – האפליקציה בנויה מיסודה ל-RTL; סגנונות וקומפוננטות `pages/*` מותאמות לימין.
- **אימות** – קומפוננטות התחברות/הרשמה עובדות מול backend OAuth/JWT; תמיכה ב-Google Sign-In באמצעות `GoogleSignIn.tsx` ו-`VITE_GOOGLE_CLIENT_ID`. בצד השרת יש **rate limiting** על רישום והתחברות (Redis) — בבדיקות עומס או ניסיונות חוזרים מהירים אפשר לקבל 429; ראו `docs/architecture/API.md` ו-`backend/README.md`.
- **ניהול קבוצות** – במסכי `GroupManage` אפשר ליצור קבוצה, לשתף קישור הזמנה, להעתיק URL בלחיצה עם פידבק חזותי (העתקה מוצלחת/שגיאה) ולסגור קבוצה.
- **צ'אט** – בפיתוח: WS ל־`chat-ws` ב־**8081** (`getChatWebSocketUrl`); בפרודקשן: `/ws` מאותו host (Nginx). **Presence:** טעינה חד־פעמית של `GET /presence/{partner}` דרך `chatWsApi` (proxy ל־8081 ב־dev); עדכון **מיידי** ב-WS: `user_online` / `user_offline`. אירועי `typing_start` / `typing_stop` מהשרת כוללים **`conversation_id`** ו־**`recipient_id`** (בנוסף ל־`user_id` ו־`type`; אופציונלי `full_name` ב־start) — כמו ב־`chat-ws` (`TypingPayload`); מסוננים בצד הלקוח מול echo של המשתמש הנוכחי. עיבוד הודעות ב־[`src/pages/MessageThread/processChatWebSocketMessage.ts`](src/pages/MessageThread/processChatWebSocketMessage.ts); בדיקות יחידה ב־[`processChatWebSocketMessage.test.ts`](src/pages/MessageThread/processChatWebSocketMessage.test.ts) משקפות את אותו חוזה. פירוט ערוצים ו-GPS: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **מפה חיה / GPS (My Bookings)** – שידור מיקום נהג/נוסע דרך `useLocationBroadcast` / `usePassengerLocationBroadcast` + `useLocationWatcher` (throttle ~1.5s, `maximumAge: 0` לשידור); קבלת עדכונים ב־`useDriverLocation` / `usePassengerLocations` (WebSocket ל־backend, reconnect). מודלים `LiveMapModal` / `LiveRideMapModal`: `watchPosition` נפרד לתצוגת “אני” עם `maximumAge: 1000`; סמנים דרך `useMapMarker` (יצירה חד־פעמית, עדכון `setPosition` בלבד). פירוט: [`docs/architecture/REALTIME.md`](../docs/architecture/REALTIME.md).
- **Zod + WebSocket** – סכימות ב־[`src/types/wsEvents.ts`](src/types/wsEvents.ts): אירועי נסיעה (`RideEventSchema`), מיקום נהג/נוסעים, צ’אט (`ChatPresenceEventSchema`), **הודעה נכנסת** (`ChatMessageSchema` → מיפוי מפורש ל־`MessageResponse` ב־`processChatWebSocketMessage`). `safeParse` גם ב־`useRideWebSocket`, `useDriverLocation`, `usePassengerLocations`, `MyRides`, `useUserEventStream`. סיכום: [`docs/ENGINEERING_HIGHLIGHTS.md`](../docs/ENGINEERING_HIGHLIGHTS.md).

למידע רחב יותר על הארכיטקטורה וההרצה הכוללת (Docker, Kubernetes, chat-ws, mobile) ראו את ה-`README` בשורש הפרויקט.

---

<!-- Original Vite README (template) below for reference -->
# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
