# API Reference

Base URL: `http://localhost:8000/api/v1` (בפרודקשן: `API_PUBLIC_URL` או דומיין).

---

## Authentication

כל endpoint שמסומן "דורש אימות" דורש header:

```
Authorization: Bearer <access_token>
```

- **Access Token**: מתקבל מ-`POST /auth/login` או `POST /auth/google-signin` או `POST /auth/refresh`. תוקף: `ACCESS_TOKEN_EXPIRE_MINUTES` (ברירת מחדל 30). כולל **`jti`** (JWT ID) ייחודי; שרת בודק **Redis denylist** (`denylist:{jti}`) לפני שמשתמש מאומת ב-HTTP — אחרי **`POST /auth/logout`** עם אותו Bearer, אותו access נחסם עד `exp` (בנוסף לניקוי refresh ב-DB).
- **Refresh Token (HttpOnly cookie)**: נשמר ב-DB (hash); מועבר ללקוח כ-**`Set-Cookie: linkup_refresh_token`** עם `HttpOnly; Secure; SameSite=lax; Path=/api/v1/auth`. תוקף: `REFRESH_TOKEN_EXPIRE_DAYS` (7). **לא חוזר בגוף ה-JSON** — הדפדפן שולח אותו אוטומטית ב-`POST /auth/refresh`. הגנת CSRF: `SameSite=lax` + path scope + POST-only endpoints.
- **לוגין מייל+סיסמה:** שגיאת אימות אחידה (**401**, `AUTH_INVALID_CREDENTIALS`) גם כשהאימייל לא רשום וגם כשהסיסמה שגויה — **מניעת username enumeration** (OWASP); אימות מייל (`is_verified`) נבדק רק אחרי אימות סיסמה מוצלח.

### Idempotency-Key (אופציונלי)

עבור **`POST /passenger/passengers/request-ride-from-search`** ניתן לשלוח כותרת **`Idempotency-Key: <uuid>`** (דפוס Stripe):

| מצב | התנהגות |
|-----|---------|
| אין כותרת | זרימה רגילה (ללא מניע duplicate ברמת Redis). |
| מפתח + גוף זהה לבקשה שכבר הושלמה ב-**201** | החזרת אותו גוף JSON ממטמון Redis (TTL ~5 דק׳). |
| מפתח בשימוש תהליכי (**PROCESSING**) | **409** + **`Retry-After: 1`**. |
| מפתח קיים עם **fingerprint** שונה (גוף שונה) | **422** — `idempotency_key_mismatch`. |

המפתח ב-Redis כולל את מזהה המשתמש (`idempotency:request_ride:{user_id}:{client_key}`); נשמרת רק תוצאת **הצלחה**; שגיאות עסקיות מסירות נעילה. Redis לא זמין → המערכת ממשיכה (**fail-open**).

**ווב:** במסך חיפוש נוסעים, הוק **`useJoinRide`** ([`useJoinRide.ts`](../../frontend/src/pages/SearchRides/useJoinRide.ts)) מחזיק מפתח יציב ב-**`useRef`** לכל ניסיון “הצטרף לנסיעה” (לא מפתח חדש בכל רינדור), ומעביר אותו ל־**`requestRideFromSearch`**; **`useSearchRides`** משתמש בו לזרימת החיפוש.

עבור **`POST /billing/checkout`** ניתן לשלוח כותרת אופציונלית **`X-Idempotency-Key`** — אידמפוטנטיות **ב-PostgreSQL** (טבלה **`idempotency_keys`**, לא Redis): fingerprint קנוני על `user_id` + נתיב + מטבע (`make_checkout_fingerprint` ב־`app/domain/billing/idempotency.py`). אם המפתח כבר קיים עם אותו fingerprint וטרם פג TTL — מוחזרת אותה תשובת JSON ואותו קוד סטטוס כמו במקור (**מטמון תשובה מלא**); fingerprint שונה על אותו מפתח → **422** — **`IDEMPOTENCY_MISMATCH`** (ראו **[ERRORS.md](../ERRORS.md)**). TTL: **`BILLING_IDEMPOTENCY_TTL_HOURS`**.

עבור **`POST /chat/conversations/{id}/messages`** ניתן (ומומלץ בלקוח) לשלוח **`Idempotency-Key`** — אופציונלי בשרת למען תאימות לאחור. אותן סמנטיקות טבלה כמו למעלה: אין כותרת → בלי Redis idempotency; מפתח + אותם `conversation_id` (בנתיב) + גוף זהה → תשובת 201 ממטמון; **409** + `Retry-After: 1` כשפעיל; **422** עם `idempotency_key_mismatch` אם המפתח שימש עם fingerprint אחר (`conversation_id` + `body`). מפתח Redis: `idempotency:chat_message:{user_id}:{client_key}`; כשל ב-Redis לפני עסקה → **fail-open**. **ווב:** [`sendMessage`](../../frontend/src/api/chat.ts) תומך במפתח אופציונלי (ברירת מחדל UUID אם לא הועבר); **[`useMessageThread`](../../frontend/src/pages/MessageThread/useMessageThread.ts)** ו-**[`useChatPopup`](../../frontend/src/components/ChatPopup/useChatPopup.ts)** מעבירים מפתח יציב לכל ניסיון שליחה (**`consumeOrCreateKey`** / **`resetOutboundKey`** ב־[**`outboundIdempotencyKey.ts`**](../../frontend/src/utils/outboundIdempotencyKey.ts)), מאחדים את תשובת ה-REST עם רשימת ההודעות דרך **`appendMessageDedupById`** כדי למנוע כפילויות עם replay או WS.

---

## Pagination

## AI Ride Parsing (shared endpoint)

- `POST /api/v1/passenger/passengers/ai-parse-search` מחזיר `AISearchResult` (מוצא/יעד/זמן/שדות הבהרה) לשימוש גם במסך חיפוש נוסעים וגם במסך יצירת נסיעה לנהג.
- במסך `CreateRide` הלקוח מחיל כללים מחמירים יותר: `departure_time` עתידי הוא חובה; `departure_date` ללא שעה מפעיל follow-up; אין שליחת חיפוש/יצירה אוטומטית.

---

### Cursor-based (נסיעות חיפוש, הודעות צ'אט, התראות משתמש)

- **נסיעות (חיפוש נוסע)** (`GET /api/v1/passenger/passengers/search-rides`): query נוסף לסינון זמן — **`departure_date`** (תאריך בלבד, יום מלא **Asia/Jerusalem**), או **`departure_time`** (נקודת זמן → חלון **±2 שעות** ב־DB), או **`departure_time`** + **`departure_time_to`** (טווח כולל). **אסור לשלב** `departure_date` עם `departure_time` / `departure_time_to` — **422**. בנוסף: `after` (opaque cursor), `limit`, `pickup_name`, `destination_name`, `search_radius`, **`destination_radius?`**, `group_id?`. תגובה: `items`, `next_cursor`, `has_more`.
- **הודעות (history)** (`GET /chat/conversations/{id}/messages`): `after` (opaque cursor בלבד) + `limit`. cursor מקודד composite key `(created_at, message_id)` דרך `app.core.pagination.cursor`, עם keyset predicate יציב ו-deterministic ordering. תגובה: `items`, `next_cursor`, `has_more`.
- **הודעות (reconnect gap)** (`GET /chat/conversations/{id}/messages/gap`): `since_message_id` (int, `>=0`) בלבד. תגובה: `items`, `truncated`, `last_message_id`. אין cursor ואין pagination contract כללי — זה endpoint ייעודי ל-WS reconnect backfill.
- **התראות משתמש** (`GET /api/v1/users/me/notifications`): `limit` (ברירת מחדל 20, עד 100), `after` (cursor אטום). תגובה: `items`, `next_cursor`, `has_more`, `limit`. סדר keyset יציב: `created_at DESC, booking_id DESC`; cursor פגום מחזיר 400.

### Page-based (הזמנות שלי)

- **הזמנות** (`GET /bookings/my-bookings`): `page` (מ-1), `limit`. תגובה: `items`, `total`, `page`, `limit`, `has_more`.

---

## Error responses

תגובות שגיאה מ-**FastAPI** (4xx/5xx) עוקבות אחר חוזה אחיד: `detail` עם שדות כמו **`error_code`**, **`message`**, **`trace_id`**, ו־**`payload`** אופציונלי. טבלת קודים, Sentry, והתאמה לפרונט ול-chat-ws — **[ERRORS.md](../ERRORS.md)**.

---

## Endpoints

### Health

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | / | לא | סטטוס כללי |
| GET | /api/v1/health | לא | בדיקת תלויות הליבה (DB, Redis, RabbitMQ) + **מצב אינפורמטיבי** של מעגלי **Circuit Breaker** (Google Maps + שליחת מייל Brevo) |

**`GET /api/v1/health`** מחזיר JSON עם לפחות:

| שדה | משמעות |
|-----|--------|
| `database` | `ok` אחרי `SELECT 1`, אחרת `error` |
| `redis` | `ok` אחרי `PING`, אחרת `error` |
| `rabbitmq` | `ok` כשהלקוח מחובר לברוקר, אחרת `error` |
| `status` | **`healthy`** רק אם כל שלושת השדות למעלה הם **`ok`**; אחרת **`unhealthy`** |
| `circuit_breakers` | אובייקט עם מפתחות **`google_geocoding`**, **`google_directions`**, **`google_distance_matrix`**, **`brevo_email`** — ערכים מחרוזתיים: **`closed`** / **`open`** / **`half_open`** (מצב מעגל in-memory בבקאנד: שלושת מעגלי Google Maps + מעגל שליחת מייל Brevo). **לא** משפיע על **`status`** — רק ניטור תפעולי. |

קוד התגובה: **200** כש־`status === healthy`, **503** כש־`status === unhealthy` (מוגדר ב־`main.py`). מימוש: **`app/infrastructure/health/health_service.py`**.

---

### Auth (`/api/v1/auth`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /register | לא | רישום — body: UserRegister (email, password, full_name, ...). מחזיר UserOut, שומר cookie לאימות מייל. **Rate limited** (Redis, אותו מנגנון כמו login/refresh). |
| POST | /login | לא | התחברות — body: LoginRequest (email, password). מחזיר LoginResponse (access_token, user) + **`Set-Cookie: linkup_refresh_token`** (HttpOnly). Rate limited. |
| POST | /refresh | לא | רענון טוקן — refresh token נקרא מ-HttpOnly cookie (לא מגוף הבקשה). מחזיר RefreshResponse (access_token, user) + cookie מעודכן. Rate limited. |
| POST | /logout | כן | ניקוי refresh ב-DB + **denylist** ל-access token מה-**`Authorization: Bearer`** + **מחיקת refresh cookie** (204). בלי Bearer — רק ניקוי refresh + cookie. |
| GET | /verify-email/confirm | לא | אימות מייל מקישור — query: email, code. מפנה לפרונט. |
| POST | /verify-email | לא | אימות מייל מקוד — body: VerifyEmailRequest (email, code). אימייל יכול מה-cookie. |
| POST | /resend-verification | לא | body: EmailOnlyRequest. |
| POST | /forgot-password | לא | query: email. Rate limited. |
| POST | /password-reset/request | לא | body: EmailOnlyRequest. |
| POST | /password-reset/confirm | לא | body: PasswordResetConfirm (email, code, new_password). |
| POST | /change-password | כן | body: ChangePasswordRequest (old_password, new_password, new_password_confirm). |
| POST | /google-signin | לא | body: GoogleSignInRequest (id_token). מחזיר LoginResponse. Rate limited. |

הערה חשובה: `LoginResponse.user` הוא payload מינימלי לזיהוי/הרשאות (למשל `user_id`, `full_name`, `email`, `is_admin`) ולא מקור פרטי פרופיל מלאים של משתמשים אחרים. שדות `partner.avatar_url` במסכי צ'אט מגיעים מ-endpoints של `chat` (`/chat/conversations*`), לא מ-login.

---

### Rides (`/api/v1/rides`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /preview-routes | כן | body: RidePreviewCreate. מחזיר אפשרויות מסלול ומחירים. |
| POST | / | כן | יצירת נסיעה — body: RideCreate. מחזיר RideResponse (201). |
| GET | /me | כן | נסיעות שלי כנהג. query: status (אופציונלי — open, full, active, completed, cancelled). **עד 200** נסיעות, ממוינות לפי `departure_time` **יורד** (מעבר לכך — נסיעות ישנות יותר לא יופיעו בתגובה). |
| PATCH | /{ride_id} | כן | עדכון חלקי — body: RideUpdate (רק בעלים). |
| POST | /{ride_id}/start | כן | התחלת נסיעה — מעביר לסטטוס ACTIVE. דורש לפחות נוסע מאושר אחד. מחזיר RideResponse. |
| POST | /{ride_id}/end | כן | סיום נסיעה — מעביר לסטטוס COMPLETED. נסיעה חייבת להיות ACTIVE. מחזיר RideResponse. |
| DELETE | /{ride_id}/cancel | כן | ביטול נסיעה (רק נהג) (204). |
| GET | /{ride_id} | לא | פרטי נסיעה. |
| WS | /ws/{ride_id} | query token=JWT | WebSocket לעדכוני סטטוס נסיעה. ערוץ Redis: `ride_{id}` (מקור שמות: `app/infrastructure/redis/keys.py`). הודעות JSON דרך `publish_ride_event` (למשל `RIDE_STARTED`, `RIDE_ENDED`, `RIDE_CANCELLED`). **שדות ללקוח:** ראו [REALTIME.md](REALTIME.md) (Broadcast). |
| WS | /ws/{ride_id}/passengers | query token=JWT | WebSocket לעדכוני מיקום נוסעים (רק נהג). ערוץ Redis: ride_{id}:passenger_locations. **שדות:** [REALTIME.md](REALTIME.md) (WebSocket JSON — מיקום). |

---

### Passenger (`/api/v1/passenger`)

שני prefix-ים: **`/passenger/passengers/*`** (בקשות נוסע, חיפוש) ו-**`/passenger/rides/*`** (פרטי נהג לנסיעה).

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /passengers/me | כן | הבקשות שלי כנוסע — **cursor paginated**. query: `request_status`, `cursor` (optional), `limit` (default 50, max 200). תגובה: `items`, `next_cursor`, `has_more`. |
| POST | /passengers/ | כן | יצירת בקשה קבועה — body: `PassengerRequestCreate` (pickup/destination, `num_passengers`, `search_radius`, `requested_departure_time` אופציונלי, `pickup_lat`/`pickup_lon` זוגיים, **`is_notification_active`** — האם לכלול את הבקשה בהתאמות אימייל/פוש כשנהג יוצר נסיעה מתאימה, **`group_id`** אופציונלי — התאמה רק לנסיעות באותה קבוצה, `is_auto_generated`). מחזיר `PassengerRequestWithMatches` (201) כולל `matching_rides` מיידי (**עד 20** התאמות ראשונות — חיפוש מרחבי עם `limit`). **זהו גם מסלול “שמירת התראה”** אחרי חיפוש: אותם פרמטרי מסלול כמו בחיפוש, בלי תלות ב-`GET search-rides` (החיפוש עצמו **לא** יוצר שורה ב-DB). |
| GET | /rides/{ride_id}/driver-info | כן | פרטי נהג לנסיעה (מנותב תחת `/api/v1/passenger/rides/...`). |
| POST | /passengers/request-ride-from-search | כן | body: `RequestRideFromSearch` (`ride_id`, `request_id?`, `num_seats`, כתובות). אם אין `request_id` — יוצר בקשה זמנית לחיפוש; אז `BookingService.request_to_join` + אירועי outbox (התראה לנהג). **כותרת אופציונלית `Idempotency-Key`** — מניע כפילות (Redis; fingerprint ב־`ride_join_idempotency.py`); ראו סעיף Idempotency-Key למעלה. |
| GET | /passengers/search-rides | אופציונלי | חיפוש נסיעות **ללא שמירה** ב-DB. query: `pickup_name`, `destination_name`, `search_radius` (ק״מ, ברירת מחדל 1), **`destination_radius?`** (ק״מ; אם קיים מחליף את רדיוס היעד בלבד), **`departure_date?`** (יום מלא Asia/Jerusalem), **`departure_time?`** (±2 שעות או תחילת טווח עם `departure_time_to`), **`departure_time_to?`**, `limit` (ברירת מחדל 20, עד 50), `after` (**opaque cursor**), **`group_id?`** — רק אם המשתמש מחובר וחבר בקבוצה. **הדדיות** בין `departure_date` לבין זוג הזמנים → **422**. **Pagination**: `items`, `next_cursor`, `has_more`. |
| DELETE | /passengers/{request_id}/cancel | כן | ביטול בקשת נסיעה ושחרור שריונים (204). בקאנד: **`CRUDBooking.bulk_cancel_bookings_for_request`** — אגרגציה + נעילת נסיעות + עדכון bulk של bookings (במקום לולאה פר־booking; ראו **`DATABASE.md`** race + migration **019**). |
| GET | /passengers/{request_id}/matches | כן | התאמות עדכניות לבקשה קיימת (**עד 20** — אותו תקרה כמו בהתאמה מיידית ביצירת בקשה). |
| GET | /passengers/all | כן | כל הנסיעות במערכת — **רק `is_admin`**; query: `filter_status`. |

---

### Bookings (`/api/v1/bookings`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /request-to-join | כן | body: BookingCreate (ride_id, request_id, num_seats). מחזיר BookingResponse (201). |
| PATCH | /{booking_id}/approve | לא (query) | query: booking_id, driver_id. אישור הזמנה. |
| PATCH | /{booking_id}/reject | לא (query) | query: booking_id, driver_id. דחיית הזמנה. |
| POST | /{booking_id}/cancel | כן | ביטול הזמנה (בעלים). |
| POST | /{booking_id}/location | כן | **GPS נהג**: body: lat, lng, heading?, speed?. דורש: משתמש=נהג הנסיעה, נסיעה ב-ACTIVE. מפיץ מיקום לנוסעים המאושרים (204). לוגיקה ב־`BookingLocationService.broadcast_driver_location` (`location_service.py`). |
| POST | /{booking_id}/passenger-location | כן | **GPS נוסע**: body: lat, lng, heading?, speed?. דורש: משתמש=נוסע הבוקינג. מפיץ מיקום לנהג בערוץ ride_{ride_id}:passenger_locations (204). לוגיקה ב־`BookingLocationService.broadcast_passenger_location` (`location_service.py`). |
| GET | /my-bookings | לא (query) | query: user_id, status?, page (default 1), limit (default 20, max 50). **Pagination**: page-based. תגובה: items, total, page, limit, has_more. |
| GET | /driver-summary | כן | **Deprecated** (OpenAPI): כל נסיעות הנהג עם נוסעים (pending/confirmed + מחזור נסיעה לפי מימוש legacy) — `DriverSummaryResponse` (`get_driver_summary`). עדיף ללקוחות חדשים: `/driver-summary/active` + `/driver-summary/history`. |
| GET | /driver-summary/active | כן | נסיעות פעילות בלבד (`open` / `full` / `active`) עם נוסעים רלוונטיים — `DriverActiveResponse`; תקרה רכה **200** שורות בבקאנד. |
| GET | /driver-summary/history | כן | נסיעות `completed` / `cancelled` עם דפדוף: query **`limit`** (ברירת מחדל 20, עד 100), **`after`** (cursor). `DriverHistoryResponse`: `rides`, `next_cursor`, `has_more`. קורסור: Base64 JSON ב־UTC דרך [`core/pagination/cursor.py`](../../backend/app/core/pagination/cursor.py). |
| GET | /passenger-summary | כן | **Deprecated** (OpenAPI): כל הזמנות הנוסע עם ride+driver+group — `PassengerSummaryResponse` (`get_passenger_summary`). עדיף: `/passenger-summary/active` + `/passenger-summary/history`. |
| GET | /passenger-summary/active | כן | הזמנות שאינן טרמינליות (כולל מחזור נסיעה) — `PassengerActiveResponse`; תקרה רכה **200**. |
| GET | /passenger-summary/history | כן | הזמנות `completed` / `cancelled` / `rejected` + `limit` / `after`. `PassengerHistoryResponse`: `bookings`, `next_cursor`, `has_more`. |
| GET | /ride/{ride_id}/manifest | לא (query) | query: ride_id, driver_id. מניפסט נסיעה (`BookingReadsService.get_ride_manifest`): עד **100** שורות; מיון **CONFIRMED** לפני **PENDING**; שדות `confirmed_total`, `pending_total`, `manifest_truncated`, `total_confirmed_passengers` (ספירת מאושרים ב-DB). |
| GET | /ride/{ride_id}/pending | לא (query) | query: ride_id, driver_id. בקשות ממתינות (`BookingReadsService.get_pending_requests`). |
| GET | /{booking_id} | לא | פרטי הזמנה. |
| WS | /ws/{booking_id}/location | query token=JWT | WebSocket לעדכוני מיקום נהג (רק נוסע הבוקינג). ערוץ Redis: booking_{booking_id}. **שדות:** [REALTIME.md](REALTIME.md) (WebSocket JSON — מיקום). |

---

### Billing (`/api/v1/billing`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /checkout | כן | יצירת Stripe Checkout Session לשדרוג פרימיום. מחזיר JSON עם `checkout_url` + `session_id` (בד"כ **201**). אופציונלי: כותרת **`X-Idempotency-Key`** — מטמון תשובה ב-DB בין מופעי API; פירוט בסעיף Idempotency למעלה. |
| GET | /status | כן | סטטוס חיוב למשתמש המחובר (`is_premium`, `premium_since`). |
| GET | /payments | כן | היסטוריית תשלומים של המשתמש המחובר. |
| POST | /webhook | לא | Stripe webhook endpoint. אימות חתימה חובה דרך `Stripe-Signature` (**fail-closed** אם חסר). Idempotency נשמרת גם ברמת אירוע Stripe (`stripe_event_id`) וגם בייחודיות תשלום. |

**רקע תפעולי:** ברקע ה-API (כש־**`BILLING_RECONCILER_ENABLED`** מופעל) רץ **`BillingReconciler`** בתדירות **`BILLING_RECONCILER_INTERVAL_SECONDS`** — מתוזמן מ־**`app/core/lifespan.py`** (APScheduler, `billing_reconciler.run`) — נעילת **`pg_try_advisory_lock`** למניעת ריצות כפולות, סריקת תשלומים **`pending`** “מיושנים”, ושאיבת סטטוס מ-Stripe למקרה שה-webhook התעכב (**`app/domain/billing/reconciler.py`**). ראו גם Prometheus תחת **`billing_reconciler_*`** ב־[`docs/operations/MONITORING.md`](../operations/MONITORING.md).

---

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /me | כן | הפרופיל שלי (UserRead). |
| PATCH | /me/last-seen | כן | עדכון `last_active_at` (204). |
| GET | /{user_id}/last-seen | כן | מקור ל-`last_seen` ב-UI צ'אט; נקרא מ-chat-ws ב-`GET /presence/{id}` כשצריך. |
| GET | /me/notifications | כן | פיד התראות cursor-based: query `limit` (default 20, max 100), `after` (cursor). תגובה: `items`, `next_cursor`, `has_more`, `limit`. מקורות מאוחדים: בקשות הצטרפות ממתינות לנהג + עדכוני הזמנות כנוסע; מיון keyset יציב `created_at DESC, booking_id DESC`. |
| PATCH | /fcm-token | כן | body: `FCMTokenUpdate` — `fcm_token` מחרוזת (רישום) או **`null`** (ניקוי ב-DB, למשל logout). |
| POST | /me/test-push | כן | בדיקת FCM (דורש `fcm_token` בפרופיל). |
| GET | /me/avatar/upload-url | כן | query: filename?. מחזיר presigned URL + staging_key. |
| POST | /me/avatar/confirm | כן | body: AvatarUploadConfirmRequest (staging_key). 202 — עיבוד ברקע. |
| DELETE | /me/avatar | כן | הסרת תמונת פרופיל (202). |
| PUT | /me | כן | body: UserUpdate. עדכון פרופיל. |

הערת גישה לקבצים: `avatar_url*` בתגובות משתמש/קבוצה — כשמוגדר **`CLOUDFRONT_DOMAIN`** ב-backend, URL ציבורי יציב דרך **CloudFront** (`https://{CLOUDFRONT_DOMAIN}/…`); אחרת **presigned GET** קצר-תוקף ל-S3. ראו `app/infrastructure/s3/service.py`.

---

### Chat (`/api/v1/chat`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /conversations | כן | body: ConversationCreate (other_user_id). יוצר או מחזיר שיחה. מחזיר ConversationDetail (201). |
| POST | /conversations/by-booking/{booking_id} | כן | שיחה לפי booking (נהג–נוסע). |
| GET | /conversations | כן | אינבוקס (רשימת שיחות): query **`limit`** (ברירת מחדל 30, עד 100), **`after`** (cursor אטום מ־`next_cursor`). תגובה: **`items`**, **`has_more`**, **`next_cursor`**. מיון בשרת: לפי `COALESCE(conversations.last_message_at, conversations.created_at)` (זמן הודעה אחרונה persisted, או `created_at` לשיחה בלי הודעות). **422** אם `after` פגום (`CHAT_INVALID_INBOX_CURSOR`). |
| GET | /conversations/{conversation_id} | כן | פרטי שיחה. `ConversationDetail` כולל גם `partner_last_read_at` וגם `partner_read_up_to_message_id` (cursor מונוטוני ל-read receipts). |
| POST | /conversations/{conversation_id}/messages | כן | body: MessageCreate (body). שליחת הודעה (**201**). אופציונלי **`Idempotency-Key`** (מומלץ בלקוח): אותו מפתח + אותה כוונה (`conversation_id` + `body`) → תגובת 201 ממטמון; **409** + `Retry-After` בתהליך; **422** `idempotency_key_mismatch` אחרת. סעיף Idempotency למעלה ו-**ADR §25**. |
| GET | /conversations/{conversation_id}/messages | כן | היסטוריית הודעות (scroll): query `limit` (default 30) + `after` (opaque cursor בלבד). מיון שרת: `created_at DESC, message_id DESC`, keyset stable tie-break. תגובה: `items`, `next_cursor`, `has_more`. שגיאת cursor פגום: `422` / `CHAT_INVALID_MESSAGE_CURSOR`. |
| GET | /conversations/{conversation_id}/messages/gap | כן | Reconnect backfill ייעודי: query `since_message_id` (`>=0`). מחזיר הודעות עם `message_id > since_message_id` בסדר עולה. תגובה: `items`, `truncated`, `last_message_id` (חובה כאשר `truncated=true`). |
| POST | /conversations/{conversation_id}/read | כן | סימון שיחה כנקראה (204). |
הערת read receipts: `POST /conversations/{conversation_id}/read` מעדכן ב־DB גם `last_read_at` וגם `last_read_message_id` עבור המשתמש הקורא. לאחר מכן מתפרסם אירוע WebSocket מסוג `message_read` עם `read_up_to_message_id`, והפרונט מסמן כ־read כל הודעה יוצאת עם `message_id <= partner_read_up_to_message_id`.

שדות רלוונטיים ב־`ConversationDetail`:
- `partner_last_read_at` — נשמר לתאימות לאחור
- `partner_read_up_to_message_id` — מקור האמת החדש ל־read receipts פר הודעה

| GET | /unread-count | כן | `{ "count": number }` — מספר שיחות עם הודעות שלא נקראו. |
| GET | /conversations/{conversation_id}/calendar.ics | כן | ייצוא ללוח שנה — כרגע `LinkUpError` **501** (`CHAT_CALENDAR_NOT_IMPLEMENTED`). |

---

### Groups (`/api/v1/groups`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | "" | כן | body: GroupCreate. יצירת קבוצה (201). |
| GET | /my | כן | הקבוצות שלי. |
| GET | /join/{invite_code} | כן | פרטי קבוצה לפי קוד הזמנה. |
| POST | /join/{invite_code} | כן | הצטרפות לקבוצה. |
| GET | /{group_id}/members | כן | רשימת חברים (חבר בלבד). |
| GET | /{group_id}/rides | כן | נסיעות של הקבוצה (חבר בלבד). **עד 200** נסיעות (ללא ביטולים ברירת מחדל), ממוינות לפי `departure_time` **יורד**. |
| POST | /{group_id}/upload-image | כן | presigned URL להעלאת תמונת קבוצה (אדמין). |
| POST | /{group_id}/confirm-image | כן | body: GroupImageConfirmRequest. אישור העלאה (אדמין). |
| DELETE | /{group_id}/image | כן | מחיקת תמונת קבוצה (אדמין). |
| DELETE | /{group_id}/members/{user_id} | כן | הסרת חבר (אדמין) (204). |
| PATCH | /{group_id}/members/{user_id}/promote | כן | קידום ל-admin. |
| DELETE | /{group_id}/leave | כן | עזיבת קבוצה (204). |
| DELETE | /{group_id} | כן | סגירת קבוצה (אדמין) (204). |
| PATCH | /{group_id} | כן | body: GroupUpdate (name, description). עדכון קבוצה (אדמין). |

---

### Geo (`/api/v1/geo`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /maps-key | לא | מחזיר google_maps_api_key (ממ-config). |
| GET | /address | כן | query: lat, lon. Reverse geocode — מחזיר כתובת. |

---

### Notifications (in-app)

**רשימת התראות:** ראו **`GET /me/notifications`** בטבלת **Users** למעלה (נתיב מלא **`GET /api/v1/users/me/notifications`** — אין רואטר נפרד תחת **`/notifications`**).

**דחיפת רענון בזמן אמת:** אין כרגע endpoint נפרד **`/api/v1/notifications/ws`** ב-FastAPI — `app/domain/notifications/router.py` ריק ולא נכלל ב־[`api_router.py`](../../backend/app/api/v1/api_router.py). עדכוני UI מתקבלים דרך **chat-ws**: אירועי **`user:{id}:events`** (פרסום מ־`WebSocketProvider` ב-backend לערוץ Redis המשותף עם chat-ws); בפרונט **`useUserEvent` / `useUserEventStream`** מזניקים רענון פיד אחרי אירועי דומיין רלוונטיים. פירוט: [`REALTIME.md`](REALTIME.md), [`NOTIFICATIONS.md`](NOTIFICATIONS.md).

---

### Admin (`/api/v1/admin`)

נתיבים בטבלה שלהלן **יחסיים** ל־**`/api/v1/admin`** (למשל **`POST /billing/reconcile/{payment_id}`** ≡ **`POST /api/v1/admin/billing/reconcile/{payment_id}`**).

דורש משתמש עם **`users.is_admin`** — `get_current_admin_user`. פעולות רגישות נרשמות בלוג **`[admin_audit]`**.

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /me | אדמין | זהות מחובר (`user_id`, `email`, `full_name`, `is_admin`). |
| GET | /health | אדמין | סיכום בריאות (כמו שירות ה-health הפנימי). |
| GET | /stats | אדמין | אגרגטים לדשבורד (משתמשים, נסיעות, בוקינגים, outbox, קבוצות וכו'). |
| GET | /users | אדמין | רשימת משתמשים. query: `q` (חיפוש email/phone/name), `is_active`, `is_admin`, `is_verified`, `limit` (עד 200). |
| PATCH | /users/{user_id}/active | אדמין | toggle `is_active` (היפוך בוליאני). |
| PATCH | /users/{user_id}/admin | אדמין | שינוי `is_admin`: query **`action=toggle`** (ברירת מחדל), **`grant`**, או **`revoke`**; אופציונלי **`reason`** ל-audit. |
| GET | /rides | אדמין | רשימת נסיעות אחרונות. query: `status` (`active` \| `completed` \| `cancelled` \| ריק), `limit` (עד 500). |
| GET | /rides/{ride_id} | אדמין | פרטי נסיעה (lookup). |
| POST | /rides/{ride_id}/cancel | אדמין | ביטול נסיעה מתפעול. |
| GET | /groups | אדמין | רשימת קבוצות. |
| GET | /outbox | אדמין | אירועי outbox. query: `status`, `event_name`, `limit`. |
| GET | /outbox/{event_id} | אדמין | פרטי אירוע. |
| POST | /outbox/{event_id}/requeue | אדמין | רק אם `status=FAILED` — מחזיר ל-`PENDING` לסריקת ה-worker. |
| GET | /bookings/{booking_id} | אדמין | פרטי הזמנה (lookup). |
| GET | /billing/payments | אדמין + capability **`admin.billing.read`** | רשימת תשלומים (תפעול). |
| GET | /billing/payments/{payment_id} | אדמין + **`admin.billing.read`** | פרטי תשלום לפי מזהה. |
| GET | /billing/stale-pending | אדמין + **`admin.billing.read`** | תשלומים **`pending`** בטווח גיל לפי הגדרות ה-reconciler (`BILLING_PENDING_*`) + **`last_reconciler_run`**. |
| POST | /billing/reconcile/{payment_id} | אדמין + **`admin.billing.read`** | ריפקוציה נקודתית מול Stripe (מחזיר `old_status` / `new_status` / `action_taken`). |

ממשק React תואם: **`ADMIN_DASHBOARD.md`** (בשורש הפרויקט).
