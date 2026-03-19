# Linkup Frontend (React + Vite)

אפליקציית ווב ב-React + TypeScript (Vite) ל-Linkup: ניהול נסיעות, קבוצות, צ'אט בזמן אמת, התחברות עם Google ואימייל/סיסמה, תמונות פרופיל (S3) ותמיכה מלאה ב-RTL בעברית.

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

- `VITE_API_URL` – בסיס ל-REST API בפרודקשן (למשל `https://api.example.com/api/v1`).  
  בפיתוח, אם לא נגדיר – נשתמש בכתובת ברירת המחדל `http://127.0.0.1:8000/api/v1` דרך proxy של Vite.
- `VITE_CHAT_WS_URL` – בסיס ל-WebSocket של הצ'אט (למשל `ws://localhost:8081/ws` או `wss://chat.example.com/ws`). אם לא הוגדר, משתמשים בכתובת שיושבת על אותו origin כמו הדפדפן.
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
- **אימות** – קומפוננטות התחברות/הרשמה עובדות מול backend OAuth/JWT; תמיכה ב-Google Sign-In באמצעות `GoogleSignIn.tsx` ו-`VITE_GOOGLE_CLIENT_ID`.
- **ניהול קבוצות** – במסכי `GroupManage` אפשר ליצור קבוצה, לשתף קישור הזמנה, להעתיק URL בלחיצה עם פידבק חזותי (העתקה מוצלחת/שגיאה) ולסגור קבוצה.
- **צ'אט** – WebSocket ל-`chat-ws` (`VITE_CHAT_WS_URL`); HTTP ל-`GET /presence/...` (`CHAT_WS_HTTP_BASE` / `VITE_CHAT_HTTP_URL`). עדכון **מיידי** כששותף מתנתק: הודעת WS `user_offline` (פולינג נשאר גיבוי).

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
