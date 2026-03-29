# פרומפט להפעלת Sentry ב-Linkup

העתק את הבלוק למטה ושלח ל-Cursor (Agent mode) כשאתה מוכן **להפעיל** את Sentry בפועל (לא רק TODO).

---

## פרומפט לקורסור — הפעלת Sentry (פרודקשן / סטייג’ינג)

### הקשר

בפרויקט כבר קיימים: `SENTRY_DSN` / `ENVIRONMENT` ב-[`backend/app/core/config.py`](../backend/app/core/config.py), `VITE_SENTRY_DSN` ב-[`frontend/.env.example`](../frontend/.env.example), תלויות `sentry-sdk[fastapi]` ו-`@sentry/react`, וכל קוד ה-init וה-capture **מוערה** ב:

- [`backend/app/core/logging.py`](../backend/app/core/logging.py)
- [`backend/app/core/exceptions/handlers.py`](../backend/app/core/exceptions/handlers.py)
- [`frontend/src/main.tsx`](../frontend/src/main.tsx)
- [`frontend/src/api/client.ts`](../frontend/src/api/client.ts)
- [`frontend/src/components/RouteErrorBoundary/RouteErrorBoundary.tsx`](../frontend/src/components/RouteErrorBoundary/RouteErrorBoundary.tsx)
- [`frontend/src/components/ChatErrorBoundary/ChatErrorBoundary.tsx`](../frontend/src/components/ChatErrorBoundary/ChatErrorBoundary.tsx)

### מה לבקש לבצע

1. **בקאנד — [`logging.py`](../backend/app/core/logging.py)**  
   - בטל הערות מ-`import sentry_sdk` עד סוף בלוק `sentry_sdk.init(...)` (רק כש-`settings.SENTRY_DSN` מוגדר).  
   - השאר את TODO על worker / chat-ws כהערה או עדכן אם מממשים שם.

2. **בקאנד — [`handlers.py`](../backend/app/core/exceptions/handlers.py)**  
   - בטל הערות: `import sentry_sdk` + `if exc.status_code >= 500: sentry_sdk.capture_exception(exc)`.

3. **פרונט — [`main.tsx`](../frontend/src/main.tsx)**  
   - בטל הערות: `import * as Sentry` + `Sentry.init({...})` (רק ב-`PROD` וכש-`VITE_SENTRY_DSN` קיים).  
   - שקול `environment` דינמי (למשל משתנה `VITE_ENVIRONMENT` או `import.meta.env.MODE`) במקום מחרוזת `"production"` קבועה אם יש סטייג’ינג.

4. **פרונט — [`client.ts`](../frontend/src/api/client.ts)**  
   - בטל הערות: import + `captureException` רק ל-`status >= 500` ב-`PROD`.

5. **פרונט — [`RouteErrorBoundary.tsx`](../frontend/src/components/RouteErrorBoundary/RouteErrorBoundary.tsx) ו-[`ChatErrorBoundary.tsx`](../frontend/src/components/ChatErrorBoundary/ChatErrorBoundary.tsx)**  
   - בטל הערות: import + `if (import.meta.env.PROD) Sentry.captureException(...)`.

6. **סביבה**  
   - אל תעלה DSN ל-Git. הגדר `SENTRY_DSN` ב-`backend/.env` ו-`VITE_SENTRY_DSN` ב-`frontend/.env` (מקומי / CI / Kubernetes secrets).  
   - ודא `uv lock` / `uv sync` ו-`npm install` אם חסרות חבילות.

7. **תיעוד**  
   - עדכן סעיף Sentry ב-[`docs/ERRORS.md`](ERRORS.md) כך שישקף `sentry_sdk.init` ב-`logging.py` (ולא רק SentryHandler ישן אם הוא לא רלוונטי).

8. **בדיקות**  
   - הרץ `uv run pytest tests/ -q`.  
   - אופציונלי: בנה `frontend` (`npm run build`) לוודא שאין שגיאות TypeScript/ESLint אחרי ביטול ההערות.

### כללים

- לא לשים DSN אמיתי בקומיט — רק בקבצי env מקומיים או בסודות פריסה.
- אם יש רעש רב ב-Sentry, הוסף `before_send` / סינון לפי `error_code` (בקאנד) או סטטוס (בפרונט).

---

## גרסה קצרה (שורה אחת לשליחה)

```
הפעל Sentry בפועל: בטל את כל ההערות ב-backend/app/core/logging.py, backend/app/core/exceptions/handlers.py, frontend/src/main.tsx, frontend/src/api/client.ts, frontend/src/components/RouteErrorBoundary/RouteErrorBoundary.tsx ו-frontend/src/components/ChatErrorBoundary/ChatErrorBoundary.tsx לפי docs/SENTRY_ENABLE_PROMPT.md; עדכן docs/ERRORS.md סעיף Sentry; אל תעלה DSN ל-git; הרץ pytest ו-build פרונט.
```
