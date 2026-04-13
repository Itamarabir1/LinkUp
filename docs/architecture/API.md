# API Reference

Base URL: `http://localhost:8000/api/v1` (בפרודקשן: `API_PUBLIC_URL` או דומיין).

---

## Authentication

כל endpoint שמסומן "דורש אימות" דורש header:

```
Authorization: Bearer <access_token>
```

- **Access Token**: מתקבל מ-`POST /auth/login` או `POST /auth/google-signin` או `POST /auth/refresh`. תוקף: `ACCESS_TOKEN_EXPIRE_MINUTES` (ברירת מחדל 30).
- **Refresh Token**: נשמר ב-DB; משמש ל-`POST /auth/refresh` לקבלת access חדש. תוקף: `REFRESH_TOKEN_EXPIRE_DAYS` (7).
- **לוגין מייל+סיסמה:** שגיאת אימות אחידה (**401**, `AUTH_INVALID_CREDENTIALS`) גם כשהאימייל לא רשום וגם כשהסיסמה שגויה — **מניעת username enumeration** (OWASP); אימות מייל (`is_verified`) נבדק רק אחרי אימות סיסמה מוצלח.

---

## Pagination

### Cursor-based (נסיעות חיפוש, הודעות צ'אט)

- **נסיעות (חיפוש נוסע)** (`GET /api/v1/passenger/passengers/search-rides`): `after` (UUID של `ride_id` אחרון בעמוד הקודם), `limit`. תגובה: `items`, `next_cursor` (= `ride_id` להמשך), `has_more`.
- **הודעות** (`GET /chat/conversations/{id}/messages`): `before` (message_id — טעינת הודעות ישנות יותר), `limit`. תגובה: `items`, `next_cursor`, `has_more`.

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
| GET | /api/v1/health | לא | בדיקת API |

---

### Auth (`/api/v1/auth`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /register | לא | רישום — body: UserRegister (email, password, full_name, ...). מחזיר UserOut, שומר cookie לאימות מייל. **Rate limited** (Redis, אותו מנגנון כמו login/refresh). |
| POST | /login | לא | התחברות — body: LoginRequest (email, password). מחזיר LoginResponse (access_token, refresh_token, user). Rate limited. |
| POST | /refresh | לא | רענון טוקן — body: RefreshRequest (refresh_token). מחזיר RefreshResponse. Rate limited. |
| POST | /logout | כן | ביטול refresh token (204). |
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
| GET | /me | כן | נסיעות שלי כנהג. query: status (אופציונלי — open, full, active, completed, cancelled). |
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
| GET | /passengers/me | כן | הבקשות שלי כנוסע. query: `request_status` (pending, approved, cancelled, matched, expired, completed, rejected). |
| POST | /passengers/ | כן | יצירת בקשה קבועה — body: `PassengerRequestCreate` (pickup/destination, `num_passengers`, `search_radius`, `requested_departure_time` אופציונלי, `pickup_lat`/`pickup_lon` זוגיים, **`is_notification_active`** — האם לכלול את הבקשה בהתאמות אימייל/פוש כשנהג יוצר נסיעה מתאימה, **`group_id`** אופציונלי — התאמה רק לנסיעות באותה קבוצה, `is_auto_generated`). מחזיר `PassengerRequestWithMatches` (201) כולל `matching_rides` מיידי. **זהו גם מסלול “שמירת התראה”** אחרי חיפוש: אותם פרמטרי מסלול כמו בחיפוש, בלי תלות ב-`GET search-rides` (החיפוש עצמו **לא** יוצר שורה ב-DB). |
| GET | /rides/{ride_id}/driver-info | כן | פרטי נהג לנסיעה (מנותב תחת `/api/v1/passenger/rides/...`). |
| POST | /passengers/request-ride-from-search | כן | body: `RequestRideFromSearch` (`ride_id`, `request_id?`, `num_seats`, כתובות). אם אין `request_id` — יוצר בקשה זמנית לחיפוש; אז `BookingService.request_to_join` + אירועי outbox (התראה לנהג). |
| GET | /passengers/search-rides | אופציונלי | חיפוש נסיעות **ללא שמירה** ב-DB. query: `pickup_name`, `destination_name`, `search_radius` (ברירת מחדל 1000 מ׳), `departure_time?`, `limit` (ברירת מחדל 20, עד 50), `after` (cursor), **`group_id?`** — רק אם המשתמש מחובר וחבר בקבוצה (dependency `require_group_member`). **Pagination**: cursor-based — `items`, `next_cursor`, `has_more`. |
| DELETE | /passengers/{request_id}/cancel | כן | ביטול בקשת נסיעה ושחרור שריונים (204). |
| GET | /passengers/{request_id}/matches | כן | התאמות עדכניות לבקשה קיימת. |
| GET | /passengers/all | כן | כל הנסיעות במערכת — **רק `is_admin`**; query: `filter_status`. |

---

### Bookings (`/api/v1/bookings`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | /request-to-join | כן | body: BookingCreate (ride_id, request_id, num_seats). מחזיר BookingResponse (201). |
| PATCH | /{booking_id}/approve | לא (query) | query: booking_id, driver_id. אישור הזמנה. |
| PATCH | /{booking_id}/reject | לא (query) | query: booking_id, driver_id. דחיית הזמנה. |
| POST | /{booking_id}/cancel | כן | ביטול הזמנה (בעלים). |
| POST | /{booking_id}/location | כן | **GPS נהג**: body: lat, lng, heading?, speed?. דורש: משתמש=נהג הנסיעה, נסיעה ב-ACTIVE. מפיץ מיקום לנוסעים המאושרים (204). |
| POST | /{booking_id}/passenger-location | כן | **GPS נוסע**: body: lat, lng, heading?, speed?. דורש: משתמש=נוסע הבוקינג. מפיץ מיקום לנהג בערוץ ride_{ride_id}:passenger_locations (204). |
| GET | /my-bookings | לא (query) | query: user_id, status?, page (default 1), limit (default 20, max 50). **Pagination**: page-based. תגובה: items, total, page, limit, has_more. |
| GET | /ride/{ride_id}/manifest | לא (query) | query: ride_id, driver_id. מניפסט נסיעה. |
| GET | /ride/{ride_id}/pending | לא (query) | query: ride_id, driver_id. בקשות ממתינות. |
| GET | /{booking_id} | לא | פרטי הזמנה. |
| WS | /ws/{booking_id}/location | query token=JWT | WebSocket לעדכוני מיקום נהג (רק נוסע הבוקינג). ערוץ Redis: booking_{booking_id}. **שדות:** [REALTIME.md](REALTIME.md) (WebSocket JSON — מיקום). |

---

### Users (`/api/v1/users`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /me | כן | הפרופיל שלי (UserRead). |
| PATCH | /me/last-seen | כן | עדכון `last_active_at` (204). |
| GET | /{user_id}/last-seen | כן | מקור ל-`last_seen` ב-UI צ'אט; נקרא מ-chat-ws ב-`GET /presence/{id}` כשצריך. |
| GET | /me/notifications | כן | כל ההתראות שלי (כנהג/נוסע). |
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
| GET | /conversations | כן | רשימת השיחות שלי. |
| GET | /conversations/{conversation_id} | כן | פרטי שיחה. |
| POST | /conversations/{conversation_id}/messages | כן | body: MessageCreate (body). שליחת הודעה (201). |
| GET | /conversations/{conversation_id}/messages | כן | הודעות. query: limit (default 30), before (message_id ל-cursor). **Pagination**: cursor-based. תגובה: items, next_cursor, has_more. |
| POST | /conversations/{conversation_id}/read | כן | סימון שיחה כנקראה (204). |
| GET | /unread-count | כן | `{ "count": number }` — מספר שיחות עם הודעות שלא נקראו. |
| GET | /conversations/{conversation_id}/calendar.ics | כן | ייצוא ללוח שנה — כרגע `LinkupError` **501** (`CHAT_CALENDAR_NOT_IMPLEMENTED`). |

---

### Groups (`/api/v1/groups`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| POST | "" | כן | body: GroupCreate. יצירת קבוצה (201). |
| GET | /my | כן | הקבוצות שלי. |
| GET | /join/{invite_code} | כן | פרטי קבוצה לפי קוד הזמנה. |
| POST | /join/{invite_code} | כן | הצטרפות לקבוצה. |
| GET | /{group_id}/members | כן | רשימת חברים (חבר בלבד). |
| GET | /{group_id}/rides | כן | נסיעות של הקבוצה (חבר בלבד). |
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

### Notifications (WebSocket)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| WS | /api/v1/notifications/ws | query token=JWT | WebSocket לפיד **התראות האפליקציה** (מסך Notifications / סנכרון עם `ChatContext`). אימות: JWT בלבד (`get_current_user_ws` → `WsUser`, ללא DB ב-connect). Redis Pub/Sub — `docs/architecture/REALTIME.md`. **פרונט (ווב):** `useChatNotificationsWebSocket` + **`onOpen`** אחרי reconnect; גיבוי polling ~5 דקות ב־`useChatNotificationsFeed`. |

רשימת התראות ב-REST: **`GET /api/v1/users/me/notifications`**.

(ראוטר: `app/domain/notifications/router.py`, נרשם ב-`api/v1/api_router.py` תחת prefix `/notifications`.)

---

### Admin (`/api/v1/admin`)

דורש משתמש עם **`users.is_admin`** — `get_current_admin_user`. פעולות רגישות נרשמות בלוג **`[admin_audit]`**.

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /me | אדמין | זהות מחובר (`user_id`, `email`, `full_name`, `is_admin`). |
| GET | /health | אדמין | סיכום בריאות (כמו שירות ה-health הפנימי). |
| GET | /stats | אדמין | אגרגטים לדשבורד (משתמשים, נסיעות, בוקינגים, outbox, קבוצות וכו'). |
| GET | /users | אדמין | רשימת משתמשים. query: `q` (חיפוש email/phone/name), `is_active`, `is_admin`, `is_verified`, `limit` (עד 200). |
| PATCH | /users/{user_id}/active | אדמין | toggle `is_active` (היפוך בוליאני). |
| PATCH | /users/{user_id}/admin | אדמין | toggle `is_admin`. |
| GET | /rides | אדמין | רשימת נסיעות אחרונות. query: `status` (`active` \| `completed` \| `cancelled` \| ריק), `limit` (עד 500). |
| GET | /rides/{ride_id} | אדמין | פרטי נסיעה (lookup). |
| POST | /rides/{ride_id}/cancel | אדמין | ביטול נסיעה מתפעול. |
| GET | /groups | אדמין | רשימת קבוצות. |
| GET | /outbox | אדמין | אירועי outbox. query: `status`, `event_name`, `limit`. |
| GET | /outbox/{event_id} | אדמין | פרטי אירוע. |
| POST | /outbox/{event_id}/requeue | אדמין | רק אם `status=FAILED` — מחזיר ל-`PENDING` לסריקת ה-worker. |
| GET | /bookings/{booking_id} | אדמין | פרטי הזמנה (lookup). |

ממשק React תואם: **`ADMIN_DASHBOARD.md`** (בשורש הפרויקט).
