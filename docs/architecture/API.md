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

---

## Pagination

### Cursor-based (נסיעות חיפוש, הודעות צ'אט)

- **נסיעות** (`GET /passenger/search-rides`): `after` (UUID של ride_id אחרון בעמוד הקודם), `limit`. תגובה: `items`, `next_cursor` (= ride_id להמשך), `has_more`.
- **הודעות** (`GET /chat/conversations/{id}/messages`): `before` (message_id — טעינת הודעות ישנות יותר), `limit`. תגובה: `items`, `next_cursor`, `has_more`.

### Page-based (הזמנות שלי)

- **הזמנות** (`GET /bookings/my-bookings`): `page` (מ-1), `limit`. תגובה: `items`, `total`, `page`, `limit`, `has_more`.

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
| WS | /ws/{ride_id} | — | WebSocket לעדכוני סטטוס נסיעה (Redis channel ride_{id}). |
| WS | /ws/{ride_id}/passengers | query token=JWT | WebSocket לעדכוני מיקום נוסעים (רק נהג). ערוץ Redis: ride_{id}:passenger_locations. |

---

### Passenger (`/api/v1/passenger`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /passengers/me | כן | הבקשות שלי כנוסע. query: request_status. |
| POST | /passengers/ | כן | יצירת בקשה — body: PassengerRequestCreate. מחזיר PassengerRequestWithMatches (201). |
| GET | /passengers/rides/{ride_id}/driver-info | כן | פרטי נהג לנסיעה. |
| POST | /passengers/request-ride-from-search | כן | body: RequestRideFromSearch (ride_id, request_id?, num_seats, pickup_name, ...). יוצר/משתמש ב-request + booking. |
| GET | /passengers/search-rides | אופציונלי | חיפוש נסיעות. query: pickup_name, destination_name, search_radius (default 1000), departure_time?, limit (default 20), after (cursor). **Pagination**: cursor-based, תגובה: items, next_cursor, has_more. |
| DELETE | /passengers/{request_id}/cancel | כן | ביטול בקשת נסיעה (204). |
| GET | /passengers/{request_id}/matches | כן | התאמות עדכניות לבקשה. |
| GET | /passengers/all | כן | כל הנסיעות (admin). query: filter_status. |

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
| WS | /ws/{booking_id}/location | query token=JWT | WebSocket לעדכוני מיקום נהג (רק נוסע הבוקינג). ערוץ Redis: booking_{booking_id}. |

---

### Users (`/api/v1/users`)

| Method | Path | Auth | תיאור |
|--------|------|------|--------|
| GET | /me | כן | הפרופיל שלי (UserRead). |
| GET | /me/notifications | כן | כל ההתראות שלי (כנהג/נוסע). |
| PATCH | /fcm-token | כן | body: FCMTokenUpdate. עדכון FCM לפוש. |
| GET | /me/avatar/upload-url | כן | query: filename?. מחזיר presigned URL + staging_key. |
| POST | /me/avatar/confirm | כן | body: AvatarUploadConfirmRequest (staging_key). 202 — עיבוד ברקע. |
| DELETE | /me/avatar | כן | הסרת תמונת פרופיל (202). |
| PUT | /me | כן | body: UserUpdate. עדכון פרופיל. |

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
| GET | /conversations/{conversation_id}/calendar.ics | כן | ייצוא ללוח שנה — כרגע 501. |

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
| WS | /api/v1/notifications/ws | query token=JWT | WebSocket להתראות למשתמש. חיבור עם token ב-query. |

(ראוטר: `app/api/websockets/notifications.py` — prefix תלוי ברישום ב-main.)
