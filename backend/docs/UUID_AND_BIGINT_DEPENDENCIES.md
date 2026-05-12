# תלויות ומשמעויות מעבר ל-UUID ו-BIGINT

מסמך זה מתאר את כל הטבלאות, השדות והנקודות בקוד (Backend + Frontend) שהושפעו או תלויים במעבר ל-**UUID** ברוב הטבלאות ול-**BIGINT** בשתי טבלאות (messages, chat_analysis).

---

## 1. סיכום טיפוסי מזהים במערכת

| טבלה | עמודת מפתח ראשי | טיפוס ב-DB / מודל | טבלאות עם FK אליה |
|------|------------------|---------------------|---------------------|
| users | user_id | **UUID** | rides, passenger_requests, bookings, conversations (x2), messages, groups, group_members |
| rides | ride_id | **UUID** | bookings |
| passenger_requests | request_id | **UUID** | bookings (request_id) |
| bookings | booking_id | **UUID** | conversations (קישור לוגי), chat |
| conversations | conversation_id | **UUID** | messages, chat_analysis |
| **messages** | **message_id** | **BIGINT** (autoincrement) | — |
| **chat_analysis** | **analysis_id** | **BIGINT** (autoincrement) | — |
| groups | group_id | **UUID** | group_members, rides.group_id, passenger_requests.group_id |
| group_members | id | **UUID** | — |
| outbox_events | id | **UUID** | — |

**שתי הטבלאות עם BIGINT:** `messages.message_id`, `chat_analysis.analysis_id`.

---

## 2. תלויות ב-Backend (Python)

### 2.1 מודלים (SQLAlchemy)

- **`backend/app/domain/users/model.py`**  
  `user_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`  
  אם ב-DB העמודה עדיין INTEGER – ה-ORM יוצר `WHERE user_id = $2::UUID` ומוסר integer → שגיאת `integer = uuid`.

- **`backend/app/domain/chat/model.py`**  
  - `Message.message_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)`  
  - `ChatAnalysis.analysis_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)`  
  כל שאר מזהי הצ'אט (conversation_id, sender_id) הם UUID.

- **`backend/app/domain/rides/model.py`**  
  `ride_id`, `driver_id` – UUID.  
  `rides.driver_id` → FK ל-`users.user_id`.

- **`backend/app/domain/bookings/model.py`**  
  `booking_id`, `ride_id`, `passenger_id`, `request_id` – UUID.

- **`backend/app/domain/passengers/model.py`**  
  `request_id`, `passenger_id` – UUID.

- **`backend/app/domain/groups/model.py`**  
  `group_id`, `admin_id`, `group_members.user_id` – UUID.

### 2.2 CRUD ו-get_by_id

- **`backend/app/domain/users/crud.py`**  
  - `get_by_id(db, id: Union[UUID, str])` – ממיר ל-`UUID(str(id))` ומחפש `User.user_id == uid`.  
  - אם ב-DB יש integer, השליפה תכשל או תחזיר None (תלוי בדרייבר).  
  - `update_refresh_token`, `update_password`, `update` – כולם עובדים על אובייקט User ומבצעים UPDATE לפי ה-PK; אם ה-PK ב-DB הוא integer והמודל UUID → אותה שגיאת integer = uuid.

- **`backend/app/domain/passengers/crud.py`**  
  `get_by_id(db, request_id: UUID)` – מצפה ל-UUID. אין תלות ב-BIGINT.

- **`backend/app/domain/chat/crud.py`**  
  - `get_messages(..., before_message_id: int | None)` – מקבל **int** (תואם ל-BIGINT).  
  - pagination מבוסס message_id לשני הכיוונים (`before` / `after`) ללא תלות ב-`created_at`.  
  - כל שאר הפונקציות משתמשות ב-`conversation_id` / `sender_id` כ-UUID.

- **`backend/app/domain/chat/ai/crud.py`**  
  עובד עם `conversation_id` (UUID). `analysis_id` לא נחשף ב-API; אין תלות קריטית בחוץ.

### 2.3 Auth ו-JWT

- **`backend/app/domain/auth/service.py`**  
  - `create_access_token(data={"sub": str(user.user_id)})` – ה-`sub` ב-JWT הוא **מחרוזת** (UUID string).  
  - `refresh_access_token`: `user_id = payload.get("sub")` ואז `get_by_id(db, id=UUID(str(user_id)))` – מצפה ש-`user_id` במסד הוא UUID, אחרת השליפה/עדכון עלולים להיכשל.  
  - כל ה-Outbox/verification משתמשים ב-`str(user.user_id)` – תואם ל-UUID string.  
  - אם `user.user_id` ב-DB הוא integer, הערך 1 יישמר כ-"1" ב-JWT; ב-`get_by_id` יהפוך ל-`UUID("1")` (ערך תקין ב-Python אך לא תואם ל-integer 1 ב-DB אם העמודה integer).

- **`backend/app/api/dependencies/auth.py`**  
  `user_id = payload.get("sub")` → `get_by_id(db, id=UUID(str(user_id)))` – אותה תלות ב-user_id כ-UUID במסד.

### 2.4 Redis ומפתחות

- **`backend/app/infrastructure/redis/keys.py`**  
  `get_otp_verification_key(user_id: str, event_name: str)` – מקבל `user_id` כ-**string**.  
  הקריאות מגיעות מ-`verification_service` עם `str(user.user_id)` – תואם ל-UUID string. אם user_id הוא integer, "1" יעבוד כמפתח אבל לא יתאים ל-UUID אחרי מיגרציה.

- **`backend/app/domain/auth/verification_service.py`**  
  `create_verification_event(user_id: str, ...)`, `verify_otp(user_id: str, ...)` – תמיד מקבלים string; הקריאות מהשירותים עוברות עם `str(user.user_id)`.

### 2.5 Outbox ו-RabbitMQ payloads

- **`backend/app/infrastructure/outbox/model.py`**  
  `OutboxEvent.payload` – JSONB. כל ה-`user_id` ב-payload נשמרים כ-`str(user.user_id)` (למשל מ-auth service, rides, וכו').

- **`backend/app/domain/notifications/core/builders/chat_builder.py`**  
  `user_id_1`, `user_id_2` ב-payload – strings (UUID).  
  **`backend/app/domain/chat/completion/service.py`**  
  `user_id_1`, `user_id_2` – strings.

- **`backend/app/domain/rides/service.py`**  
  `publish_to_outbox(db, "ride.created", {"ride_id": str(new_ride.ride_id)})` – UUID כ-string.

- **`backend/app/workers/tasks/ride_task.py`**  
  `"user_id": str(user_id_raw)` – מצפה ש-user_id יומר ל-string (UUID).

- Workers (avatar_tasks, chat_summary_task, notification_tasks) שמקבלים `user_id` מה-payload ומריצים `get_by_id(db, id=UUID(str(user_id)))` – תלויים ב-user_id כ-UUID במסד.

### 2.6 Chat – message_id ו-before_message_id

- **`backend/app/domain/chat/schema.py`**  
  `MessageResponse.message_id: int` – תואם ל-BIGINT. חשוב שה-API לא ישלח string (למשל מ-JSON) כי הפרונט מצפה ל-number.

- **`backend/app/domain/chat/service.py`**  
  - מחזיר `message_id=msg.message_id` (int) ב-response וב-publish ל-Redis.  
  - `get_messages(..., before_message_id: int | None)` – pagination לפי message_id (BIGINT).

- **`backend/app/api/v1/routers/chat.py`**  
  `before_message_id: int | None = Query(None)` – query param כ-int.

- **`backend/app/infrastructure/events/publishers/redis.py`**  
  payload של הודעות צ'אט כולל `message_id` – בערך מספרי (BIGINT) כדי שהצרכנים (למשל chat-ws) לא יישברו.

### 2.7 S3 וקבצים

- **`backend/app/infrastructure/s3/service.py`**  
  `uid_str = str(user_id)` – משמש לבניית paths. תואם ל-UUID string. ~~אם user_id הוא integer, המחרוזת "1" תעבוד אבל אחרי מיגרציה ל-UUID המבנה ישתנה.~~ **עדכון (H8):** type annotation תוקן מ-`UUID | int | str` ל-`UUID | str` — vestigial `int` הוסר.

### 2.8 שאר השירותים

- **Bookings, Rides, Passengers, Groups** – כולם עובדים עם UUID ל-user_id, ride_id, booking_id, request_id, group_id. כל ה-`UUID(str(...))` או `str(...)` ב� payloads תואמים למצב UUID.

---

## 3. תלויות ב-Frontend (TypeScript)

### 3.1 טיפוסים גלובליים

- **`frontend/src/types/api.ts`**  
  - `User.user_id: string`  
  - `Ride.ride_id`, `driver_id`, `group_id`: string (או null)  
  - `PassengerRequest.request_id`, `passenger_id`, `group_id`: string  
  - `Booking.booking_id`, `ride_id`, `request_id`, `passenger_id`: string  
  - `Group.group_id`, `admin_id`: string  
  - `GroupMember.id`, `group_id`, `user_id`: string  
  כולם תואמים ל-UUID כ-string ב-JSON.

### 3.2 צ'אט והודעות (BIGINT)

- **`frontend/src/api/chat.ts`**  
  - `MessageResponse`: `message_id: number`, `conversation_id: string`, `sender_id: string`.  
  - `getMessages(conversationId, params?: { limit?: number; before?: number; after?: number })` – cursorים כ-number (תואם ל-BIGINT).  
  חשוב: אם ה-API יחזיר `message_id` כמחרוזת (למשל "1234567890123456789"), ב-JS מספרים מעל 2^53 מאבדים דיוק – לכן BIGINT גדול מאוד עלול לדרוש טיפול כ-string בפרונט אם יגדלו המזהים. כרגע עם autoincrement סביר שיישאר בטווח בטוח.

- **`frontend/src/pages/MessageThread.tsx`**  
  `key={m.message_id}` – משתמש ב-message_id כ-key; TypeScript מצפה ל-`MessageResponse` עם `message_id: number`.

- **`frontend/src/pages/Messages.tsx`**  
  `conversation_id` כ-string (UUID) ב-routes ורשימת שיחות.

- **`frontend/src/pages/MyBookings/index.tsx`**, **`frontend/src/pages/Notifications.tsx`**  
  ניווט ל-`/messages/${conversation.conversation_id}` – conversation_id כ-string (UUID).

---

## 4. מיגרציות (Alembic)

- **`backend/alembic/versions/001_full_schema.py`**  
  - יוצר `users` עם `user_id UUID` רק ב-`CREATE TABLE IF NOT EXISTS` – אם הטבלה כבר קיימת עם INTEGER, היא לא משתנה.  
  - `rides`, `bookings`, `passenger_requests`, `conversations`, `messages`, `groups`, `group_members` – מוגדרים עם UUID ל-user references; `messages.message_id` כ-BIGSERIAL (או מקביל), `chat_analysis.analysis_id` דומה.  
  - הוספת FK מ-groups/group_members ל-users מותנית ב-`users.user_id` כ-uuid.

- מיגרציה עתידית שממירה `users.user_id` מ-INTEGER ל-UUID חייבת לעדכן גם את כל ה-FK והמפתחות ב-Redis/outbox שמשתמשים ב-user_id הישן (למשל אם נשמר מזהה מספרי ב-JWT או ב-payloads).

---

## 5. רשימת בעיות / סיכונים שעלו במעבר

> **H8 fix (תוקן):** שאריות `user_id: int` ב-type annotations תוקנו — `users/service.py` (4 מתודות: `get_user_by_id`, `update_user_location`, `update_user_info`, `update_fcm_token`), `exceptions/user.py` (`UserNotFoundError.__init__`: `int | None` → `UUID | str | None`), `chat/calendar_export.py` (`conversation_id: int` + `current_user_id: int` → `UUID`), `s3/service.py` (`UUID | int | str` → `UUID | str`). קוד מת עם `int` ב-`users/router.py` הוסר. DB PK כבר היה `PG_UUID(as_uuid=True)` — הבאג היה רק ב-Python type hints.

1. **users.user_id עדיין INTEGER ב-DB**  
   - ~~ה-ORM והמודל מצפים ל-UUID → UPDATE/WHERE עם cast ל-UUID וערך integer → `operator does not exist: integer = uuid`.~~ **תוקן:** DB ו-ORM כבר UUID; שאריות `int` ב-type annotations תוקנו (H8).  
   - **פתרון:** מיגרציה שממירה את `users.user_id` (וכל ה-FK אליו) ל-UUID, או workaround עם SQL ישיר בלי cast (זמני).

2. **JWT `sub` ו-refresh**  
   - אם user_id במסד הוא integer, `sub` יכול להיות "1". אחרי מיגרציה ל-UUID, טוקנים ישנים עם `sub="1"` לא יתאימו יותר ל-user_id החדש (UUID).  
   - **פתרון:** אחרי מיגרציה, משתמשים עם טוקנים ישנים יצטרכו להתחבר מחדש; או לוגיקה חד-פעמית למפת old_id → new UUID (מורכב).

3. **Redis OTP / verification**  
   - מפתחות בנויים מ-`user_id` כ-string. אם עברת מ-integer ל-UUID, מפתחות ישנים (`otp:email_verification:1`) לא יתאימו ל-UUID החדש.  
   - **פתרון:** אחרי מיגרציה, קודי אימות ישנים פגי תוקף ממילא; אין צורך במפתחות ל-UUID הישן.

4. **Outbox / RabbitMQ payloads**  
   - payloads שמכילים `user_id` כ-string – אחרי מיגרציה יהיו UUID strings. Workers שקוראים `UUID(str(user_id))` יתנהגו נכון.  
   - אם אי-שם נשמר user_id כמספר (int) ב-JSON, יש לתקן ל-string (UUID).

5. **message_id / analysis_id כ-BIGINT**  
   - ב-Python הם `int`; ב-JSON נשלחים כמספר. בפרונט `message_id: number` – ב-JS מספרים מעל 2^53 לא בטוחים; עם autoincrement סביר שלא יגיעו לשם.  
   - **סיכון:** אם בעתיד יוסיפו יצירת message_id מחוץ ל-DB (למשל UUID), כל המקומות שמצפים ל-int (schema, get_messages pagination, פרונט) יצטרכו עדכון.

6. **get_by_id ו-dependencies**  
   - כל הקריאות ל-`crud_user.get_by_id(db, id=UUID(str(user_id)))` מניחות ש-user_id במסד הוא UUID.  
   - אם המסד עדיין integer והדרייבר מחזיר 1, אז `user.user_id == 1` ו-commit על אותו אובייקט יוצר את שגיאת integer = uuid; אין בעיה ב-get_by_id עצמו אם השליפה עובדת (למשל עם raw SQL או אם הדרייבר ממיר 1 ל-UUID כלשהו – תלוי בהגדרות).

7. **S3 paths**  
   - בנויים מ-`str(user_id)`. מעבר מ-1 ל-UUID משנה את מבנה הנתיבים; קבצים ישנים יישארו תחת נתיב עם "1" וחדשים תחת UUID – צריך החלטה אם להעביר או להשאיר backward compatibility.

8. **Frontend – כל ה-IDs כ-string**  
   - חוץ מ-`message_id` (ו-cursors `before`/`after`) שהם number – תואם ל-UUID כ-string ול-BIGINT כ-number.

---

## 6. טבלת קבצים מרכזיים לפי נושא

| נושא | קבצים |
|------|--------|
| מודל User ו-user_id | `backend/app/domain/users/model.py` |
| מודל Message/ChatAnalysis ו-BIGINT | `backend/app/domain/chat/model.py` |
| Auth + JWT sub | `backend/app/domain/auth/service.py`, `backend/app/api/dependencies/auth.py` |
| CRUD User + get_by_id | `backend/app/domain/users/crud.py` |
| Chat pagination (before/after by message_id) | `backend/app/domain/chat/crud.py`, `backend/app/domain/chat/service.py`, `backend/app/domain/chat/router.py`, `frontend/src/api/chat.ts` |
| סכמות צ'אט (message_id int) | `backend/app/domain/chat/schema.py` |
| Redis OTP keys | `backend/app/infrastructure/redis/keys.py`, `backend/app/domain/auth/verification_service.py` |
| Outbox/RabbitMQ payloads | `backend/app/domain/auth/service.py`, `backend/app/domain/notifications/core/builders/chat_builder.py`, `backend/app/domain/chat/completion/service.py`, `backend/app/workers/tasks/ride_task.py` |
| Workers (user_id מה� payload) | `backend/app/workers/tasks/avatar_tasks.py`, `backend/app/workers/tasks/chat_summary_task.py`, `backend/app/workers/tasks/notification_tasks.py` |
| S3 paths | `backend/app/infrastructure/s3/service.py` |
| פרונט – טיפוסים | `frontend/src/types/api.ts`, `frontend/src/api/client.ts` |
| פרונט – צ'אט | `frontend/src/pages/MessageThread.tsx`, `frontend/src/pages/Messages.tsx` |
| מיגרציה | `backend/alembic/versions/001_full_schema.py` |

---

סיום המסמך. לעדכונים אחרי מיגרציה או שינויי טיפוס – עדכן את הסעיפים הרלוונטיים ואת טבלת הקבצים.
