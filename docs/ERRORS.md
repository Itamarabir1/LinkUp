# Linkup — Error handling

מדריך אחיד לשגיאות בין **FastAPI (backend)**, **chat-ws (Go)** והפרונט.

---

## 1. פורמט JSON (REST)

כל תגובת שגיאה מובנית מה-API הראשי (ולמסלולי HTTP ב-chat-ws שמחזירים JSON) עוקבת אחרי:

```json
{
  "status": "error",
  "error_code": "BOOKING_NOT_FOUND",
  "message": "ההזמנה לא נמצאה",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "details": {}
}
```

- **`status`**: תמיד `"error"` בתגובות מטופלות ע״י ה-handlers.
- **`error_code`**: מזהה יציב ללקוחות וללוגים — **SCREAMING_SNAKE_CASE**.
- **`message`**: טקסט להצגה למשתמש (בדרך כלל בעברית בדומיינים פנימיים).
- **`trace_id`**: מזהה למעקב — ב-backend זה **`request_id`** מה-middleware (מופיע גם בכותרת `X-Request-ID` כשמוגדר). ב-chat-ws: אם נשלח `X-Request-ID` — משתמשים בו; אחרת מזהה קצר אקראי.
- **`details`**: אופציונלי. לדוגמה ב-**`VALIDATION_ERROR`**: `details.fields` — מערך `{ "field", "message" }`.

דוגמה ל-**validation** (422):

```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "שגיאת וולידציה בנתונים שהתקבלו",
  "trace_id": "...",
  "details": {
    "fields": [{ "field": "email", "message": "שדה חובה" }]
  }
}
```

---

## 2. טבלת `error_code` (עיקריים)

| error_code | HTTP | שירות | מתי נזרק |
|------------|------|--------|----------|
| VALIDATION_ERROR | 422 | backend | Pydantic `RequestValidationError` |
| DATABASE_CONFLICT | 409 | backend | SQLAlchemy `IntegrityError` |
| DATABASE_ERROR | 500 | backend | `SQLAlchemyError` (לא integrity) |
| AUTH_* / INVALID_PASSWORD / … | לפי המחלקה | backend | דומיין auth (`app/core/exceptions/auth.py`) |
| USER_* | לפי המחלקה | backend | משתמשים |
| RIDE_* | לפי המחלקה | backend | נסיעות |
| BOOKING_* / NO_SEATS_AVAILABLE | לפי המחלקה | backend | הזמנות |
| PSG_* | לפי המחלקה | backend | נוסעים |
| VAL_* / INVALID_LOCATION / INSUFFICIENT_SEATS / … | לפי המחלקה | backend | ולידציה |
| INFRA_* / GEO_* / RATE_LIMIT_EXCEEDED | לפי המחלקה | backend | תשתית, גיאוקוד, rate limit |
| S3_UPLOAD_FAILED / S3_DELETE_FAILED | 502 | backend | S3 |
| REDIS_UNAVAILABLE | 503 | backend | Redis |
| WORKER_TASK_FAILED | 500 | backend | משימות worker |
| EXTERNAL_SERVICE_ERROR | 502 | backend | שירות חיצוני כללי |
| CHAT_ROOM_NOT_FOUND | 404 | backend | צ׳אט |
| CHAT_UNAUTHORIZED_ACCESS | 403 | backend | צ׳אט |
| CHAT_MESSAGE_SEND_FAILED | 500 | backend | צ׳אט |
| NOTIFICATION_* | לפי המחלקה | backend | התראות |
| METHOD_NOT_ALLOWED / UNAUTHORIZED / INVALID_TOKEN / BAD_REQUEST / REDIS_UNAVAILABLE | לפי הקוד | chat-ws | HTTP ב-presence / לפני WebSocket upgrade |

רשימה מלאה: קבצים תחת `backend/app/core/exceptions/`.

---

## 3. `trace_id` לעומת `request_id`

- ב-**backend**, ה-middleware מגדיר **`request.state.request_id`** (UUID) לכל בקשה. אותו ערך נשלח בגוף JSON כ-**`trace_id`** בתגובות שגיאה מטופלות, ולעיתים גם בכותרת **`X-Request-ID`**.
- המונח **`trace_id`** ב-JSON הוא השדה הסטנדרטי ללקוח (כולל פרונט) כדי להציג למשתמש או לשלוח לתמיכה; ערכו בפועל הוא ה-**request id** של אותה בקשה.
- ב-**chat-ws**, אם הלקוח שולח **`X-Request-ID`**, אותו ערך יופיע ב-**`trace_id`** בתגובת JSON; אחרת נוצר מזהה קצר.

---

## 4. איך מוסיפים שגיאה חדשה

### שלב א — Backend (Python)

1. אם השגיאה שייכת לדומיין קיים: הוסיפו מחלקה ב-`app/core/exceptions/<domain>.py` שיורשת מ-`LinkupError`, עם `error_code` ב-**SCREAMING_SNAKE_CASE** ו-`status_code` מתאים.
2. ייצאו מ-`app/core/exceptions/__init__.py` (ו-`__all__`).
3. בשרות/ראוטר: `raise YourNewError(...)` במקום `HTTPException` או `return None` כשמשאב חסר (העדיפו `*NotFoundError` מתאים).

**אל** ליצור קובץ exceptions חדש מעבר לדומיינים הקיימים, למעט מדיניות הפרויקט (למשל `chat.py`).

### שלב ב — chat-ws (Go), אם רלוונטי

1. השתמשו ב-`internal/errors.AppError` (או עטיפה עם `fmt.Errorf("...: %w", err)`) ללוגיקה פנימית.
2. **HTTP**: החזירו JSON באותו מבנה (`status`, `error_code`, `message`, `trace_id`) — ראו `internal/api/json_error.go`.
3. **WebSocket**: בשגיאות סגירה — **רק** קוד סגירה RFC 6455 (למשל 1008 מדיניות, 1011 שרת); **לא** לשלוח JSON על גבי ה-WS בעת סגירה.

### שלב ג — Frontend

1. אם צריך מיפוי ייעודי בעברית ב-UI: הוסיפו `error_code` ל-`CODE_MESSAGES` ב-`src/errors/useErrorHandler.ts` (אופציונלי — ברירת המחדל היא להשתמש ב-`message` מהשרת).
2. ודאו שהבקשה עוברת דרך `api` מ-`src/api/client.ts` כדי שיופיעו לוגים/עתיד Sentry על שגיאות שאינן 401.

---

## 5. Sentry Integration

כשמחברים Sentry:

1. **Backend — `app/core/logging.py`**: הוסיפו handler של Sentry (למשל `SentryHandler`) ל-root logger, בהתאם לתיעוד Sentry ל-Python, כך שחריגות ולוגי שגיאה יישלחו עם הקשר (כולל `request_id` אם מסננים/מצרפים אותו ב-filters).
2. **Frontend — `src/api/client.ts`**: הסירו הערה והפעילו `Sentry.captureException(err)` בתוך ה-interceptor שמטפל ב-4xx/5xx שאינם 401 (מסומן `// TODO: Sentry`).
3. **Frontend — `src/components/RouteErrorBoundary/RouteErrorBoundary.tsx`** ו-**`src/components/ChatErrorBoundary/ChatErrorBoundary.tsx`**: הפעילו `Sentry.captureException(error)` ב-`componentDidCatch` (מסומן `// TODO`).

---

## קישורים

- ארכיטקטורה כללית: [../ARCHITECTURE.md](../ARCHITECTURE.md)
- Backend README: [../backend/README.md](../backend/README.md)
