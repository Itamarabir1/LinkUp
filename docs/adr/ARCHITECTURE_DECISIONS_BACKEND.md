# החלטות ארכיטקטוניות — Backend ו-Worker

מסמך להצגה בראיון: **למה** הבקאנד וה-worker בנויים כפי שהם, עם דגש על **סקייל**, **אמינות** ו**תפעול**.

---

## 1. PostgreSQL + PostGIS

| | |
|--|--|
| **הקשר** | נסיעות, מיקומים, חיפוש מרחבי, יחסים בין משתמשים–הזמנות–קבוצות. |
| **החלטה** | PostgreSQL כ-DB ראשי; **PostGIS** לגיאומטריה ושאילתות מרחק/אזור. |
| **למה (כולל סקייל)** | ACID לטרנזקציות עסקיות; שאילתות מורכבות ואינדקסים (ראו `docs/architecture/DATABASE.md`); מודל יחסי מתאים לדומיין נסיעות. |
| **אלטרנטיבות** | Mongo לבד — פחות טבעי לטרנזקציות צולבות-טבלאות; SQLite — לא לפרודקשן מרובה-מופעים. |
| **בקצרה לראיון** | "רצינו DB יחסי חזק עם תמיכה מובנית בגיאו לחיפוש טרמפים לפי מרחק ואזור." |

---

## 2. Redis — מופע אחד, שני logical DB (0 ו-1)

| | |
|--|--|
| **הקשר** | Cache, rate limit, pub/sub, presence, צ'אט, אירועי משתמש ל-WS. |
| **החלטה** | **DB 0** — backend/worker: cache (למשל geocode 24h, ride preview 24h), `broadcast` לרשימת נסיעות, OTP, rate limit auth. **DB 1** — pub/sub שמשותף ל-**chat-ws** ול-backend: הודעות צ'אט, `user:{id}:events`, completion, presence. |
| **למה** | הפרדת namespace: פעולות cache/eviction על DB0 לא מוחקות או מתנגשות עם ערוצי צ'אט ב-DB1; אותו שרת Redis פשוט לפריסה. |
| **בקצרה לראיון** | "חילקנו Redis לוגית כדי שה-cache וה-broadcast לא ייפגעו ב-pub/sub של הצ'אט." |

---

## 3. RabbitMQ ותורי Worker

| | |
|--|--|
| **הקשר** | אירועי דומיין מובילים למייל, FCM, עיבוד תמונות, משימות מתוזמנות. |
| **החלטה** | Outbox → פרסום ל-RabbitMQ; consumers נפרדים ל-**`notifications_queue`**, **`avatar_upload_queue`**, **`scheduled_tasks_queue`** (ראו `docs/architecture/EVENTS.md`). |
| **למה (סקייל)** | **הפרדת עומס**: תור התראות כבד (מייל + FCM) לא חוסם עיבוד תמונות S3; משימות מתוזמנות לא תוקעות שליחת התראות מיידיות. ניתן לסקייל consumers לפי תור. |
| **למה לא Kafka (בשלב זה)** | מפורש ב-`ARCHITECTURE.md` — RabbitMQ מספיק לסקייל הנוכחי, פשטות תפעול. |
| **בקצרה לראיון** | "פרדנו תורים כדי של-worker אחד לא יהיה צוואר בקבוק בין התראות לעיבוד אווטאר." |

---

## 4. Outbox pattern

| | |
|--|--|
| **הקשר** | אחרי commit ל-DB צריך לשלוח אירוע לברוקר בלי לאבד אותו אם השרת קורס. |
| **החלטה** | כתיבת שורה ל-`outbox_events` **באותה טרנזקציה** עם השינוי העסקי; worker (`notification-worker`) מפרסם ל-RabbitMQ (LISTEN/NOTIFY + fallback). |
| **דוגמאות routing keys** | לדוגמה: `ride.created`, `ride.cancelled_by_driver`, `booking.passenger_join_request`, `booking.approved_by_driver`, `booking.rejected_by_driver`, `auth.email_verification`, `auth.password_reset_code`, `user.registered` — רשימה מלאה ב-`docs/architecture/EVENTS.md`. |
| **למה** | **At-least-once**; ה-API לא תלוי ב-latency או זמינות הברוקר בזמן התשובה ללקוח. |
| **אלטרנטיבה** | Publish ישיר אחרי commit — race/crash עלולים לאבד אירוע. |
| **בקצרה לראיון** | "אאוטבוקס מבטיח שהאירוע והנתונים ב-DB יהיו עקביים — זה דפוס מוכר במערכות event-driven." |
| **מקביליות workers** | משיכת PENDING עם **`FOR UPDATE SKIP LOCKED`** — מספר פרוסות `notification-worker` לא נתקעות אחת על השנייה על אותה שורה; ראו [FEATURE_DECISIONS.md §outbox-skip-locked](../FEATURE_DECISIONS.md#outbox-skip-locked), [`outbox/repository.py`](../../backend/app/infrastructure/outbox/repository.py). |

---

## 5. רינדור מיילים — שירות Node.js (Express, React Email)

| | |
|--|--|
| **הקשר** | רינדור מיילים בוצע מקומית ב-Jinja2 בתוך הבקאנד; נדרש מעבר לתבניות מודרניות, רכיבים משותפים עם הפרונט ו-preview נוח. |
| **החלטה** | מיקרו-שירות **`email-renderer`** (Node.js + TypeScript + Express + React / `@react-email/components`) מחזיר HTML; הבקאנד ו-**`notification-worker`** (מסלול Outbox/התראות) שולחים `template + props` ל-**`POST /render`**. |
| **למה Node.js** | תבניות מבוססות **React Email** נרנדרות בשרת עם **`renderToStaticMarkup`** — אותו דפוס כמו SSR בדפדפן, בלי להטמיע מנוע JavaScript בתוך תהליך Python; TypeScript וכלים (`react-email`) מיושרים לצוות הפרונט. |
| **למה (סקייל / תפעול)** | **הפרדת אחריות**: orchestration, Outbox ושליחת SMTP נשארים ב-Python; רינדור HTML מרוכז בשירות שניתן לסקייל, לגרסאות ולפריסה עצמאית. |
| **חוזה** | `EMAIL_MAP` בבקאנד משתמש ב-template names ב-**PascalCase**; ב-renderer יש `TEMPLATE_REGISTRY` + אימות fail-fast מול `EMAIL_MAP_KEYS` בזמן startup. |
| **Trade-off** | תלות רשת נוספת (timeout, health, סדר עלייה). ב-Docker Compose: **healthcheck** ו-**`depends_on`** מ-`email-renderer` ל-`backend` ול-**`notification-worker`**. |
| **אלטרנטיבות** | להישאר ב-Jinja2 בלבד; MJML/ HTML סטטי בלי קומפוננטות; או ספק SaaS לתבניות — פחות שליטה ושכפול לוגיקה מול המוצר. |
| **בקצרה לראיון** | "העברנו רינדור מייל לשירות Node עם React Email כדי לשמור על תבניות מודרניות ו-SSR טבעי; Python ממשיך לנהל אירועים ואמינות דרך Outbox." |

---

## 6. תזמון (scheduled work)

| | |
|--|--|
| **הקשר** | תזכורות נסיעה, תחזוקה, timeout לצ'אט, סריקת דלק. |
| **החלטה** | לולאת **publisher** קלה ב-worker (~**60 שניות**) שבודקת "הגיע הזמן" ודוחפת routing keys ל-exchange `scheduled`; הלוגיקה הכבידה רצה ב-**consumer** של `scheduled_tasks_queue`. מרווחים אופייניים: תזכורות ~**5 דקות**, תחזוקה ~**25 דקות**, chat timeout ~**שעה**, דלק ~**יומי** (ראו `docs/ENGINEERING_HIGHLIGHTS.md` סעיף 2א). |
| **למה** | הפרדה בין "מתזמן דק" לבין "עובד כבד" — קל להרחבה, לוגים וניטור. תזכורות מבוססות טבלת **`scheduled_notifications`** (מיגרציה 008) במקום דגלי `reminder_sent` על rides/bookings — מקור אמת אחד לתזמון. |
| **בקצרה לראיון** | "לא רצינו cron אחד ענק; דוחפים משימות לתור וה-worker המאוחד מבצע." |

---

## 7. Python, FastAPI, async SQLAlchemy

| | |
|--|--|
| **החלטה** | API ב-**FastAPI**; גישה ל-DB ב-**async** SQLAlchemy 2.0 בדומיינים ליבה (passengers, bookings, rides); workers רצים מתוך אותו codebase (**`notification-worker`**, **`task-worker`**, **`ai-worker`**). |
| **למה** | מהירות פיתוח, אקוסיסטם; async מתאים ל-I/O כבד (DB, HTTP חיצוני) תחת עומס. |
| **סקייל** | אין `Session.run_sync` בזרימות אפליקציה — רק Alembic; workers עם `await db.execute(select(...))` במקום חסימות מיותרות. |
| **בקצרה לראיון** | "Python ללוגיקה עסקית ואינטגרציות; async כדי לא לחסום את ה-event loop על DB." |

---

## 8. Uvicorn workers ו-connection pool ל-Postgres

| | |
|--|--|
| **החלטה** | מספר workers לפי `UVICORN_WORKERS` (Docker); `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `pool_pre_ping` מ-config. **`statement_timeout`** דו-שכבתי: **`DB_STATEMENT_TIMEOUT_MS`** מוחל ברמת session דרך `connect_args.server_settings` ב-`app/db/session.py` (ערך אופרטיבי, default 30s); מיגרציה **017** קובעת ceiling דיפנסיבי **קשיח** של 60s ברמת role (literal — דטרמיניסטי בלי תלות ב-runtime config). רשימות נסיעות לנהג ולקבוצה (`/rides/me`, `/groups/{id}/rides`) משתמשות ב-keyset cursor pagination (`limit`/`after`) על `(departure_time DESC, ride_id DESC)` עם אינדקסים מורכבים (**018**). |
| **למה (סקייל)** | יותר workers = יותר בקשות מקביליות, אבל כל worker משתמש בחיבורי pool — צריך איזון מול מגבלות Postgres. **`pool_pre_ping`** מפחית כשלי חיבור מתים אחרי recycle של השרת. **`statement_timeout`** ברמת session = שינוי `.env` תקף ב-restart בלי מיגרציה. ה-ceiling ברמת role מספק defense-in-depth מול connections ישירים שעוקפים את ה-engine. keyset pagination לרשימות נסיעות מפחית סריקות עמוקות ו-payload גדול לעומת cap קשיח יחיד. |
| **בקצרה לראיון** | "מגדילים replicas ו-workers בזהירות מול גודל ה-pool — זה trade-off קלאסי." |

---

## 9. נעילות ורaces (הזמנות)

| | |
|--|--|
| **החלטה** | `SELECT ... FOR UPDATE` על נסיעה באישור/ביטול הזמנה; התראות ביטול נסיעה רק לבוקינגים ב-**PENDING** או **CONFIRMED**. |
| **למה** | מניעת race conditions תחת בקשות מקביליות; פחות "רעש" והתראות שגויות. |
| **בקצרה לראיון** | "נעילה פסימית היכן שיש תחרות על אותה נסיעה." |

---

## 10. Cursor pagination

| | |
|--|--|
| **החלטה** | חיפוש נסיעות והודעות צ'אט עם `after` / `before` + `limit`, לא offset גדול בלבד. |
| **למה (סקייל)** | Offset עמוק על טבלאות גדולות יקר; cursor יציב יותר תחת נתונים שגדלים. |
| **בקצרה לראיון** | "Cursor pagination לרשימות שיכולות לגדול מאוד." |

---

## 11. S3 ו-CloudFront (אופציונלי)

| | |
|--|--|
| **החלטה** | העלאות עם **presigned PUT**; אווטאר משתמש ב-prefix **גרסתי** `avatars/{user_id}/v{version}/`; מחיקת גרסה קודמת ב-S3 אחרי commit ל-DB. קריאה: אם מוגדר **`CLOUDFRONT_DOMAIN`** — URL ציבורי יציב; אחרת presigned GET. |
| **למה** | ה-API לא מזרים bytes של תמונות; CDN מפחית עומס על ה-API ומאפשר caching בצד CDN. |
| **בקצרה לראיון** | "אחסון אובייקטים ב-S3, חתימה לזמן קצר או CloudFront ליציבות URL." |

---

## 12. אבטחה ועומס (auth)

| | |
|--|--|
| **החלטה** | bcrypt דרך **thread pool** (`run_in_executor`) כדי לא לחסום event loop; rate limit על register/login (Redis); OTP עם `secrets` + `hmac.compare_digest`; לוגין עם **אותה תגובת שגיאה** לאימייל לא קיים ולסיסמה שגויה (מניעת user enumeration). |
| **למה** | תחת הרשמות/לוגין מקביליים bcrypt עלול לרסן את כל ה-API אם רץ על הלולאה הראשית. |
| **בקצרה לראיון** | "הפרדנו CPU כבד של סיסמאות ל-thread pool כדי לשמור על רספונסיביות של ה-API." |

---

## 13. WebSocket על FastAPI — JWT בלי DB ב-handshake

| | |
|--|--|
| **הקשר** | WS לנסיעות, מיקום, פיד התראות in-app. |
| **החלטה** | `get_current_user_ws` מאמת **רק JWT** ומחזיר `WsUser` — **בלי SELECT ל-DB** בזמן החיבור. |
| **למה (סקייל)** | אלפי חיבורי WS פותחים לא מציפים את pool ה-DB; trade-off: לא בודקים `is_active` ב-handshake עד פקיעת הטוקן. |
| **פירוט מלא** | [WEBSOCKETS.md](WEBSOCKETS.md). |
| **בקצרה לראיון** | "בחיבור WS דילגנו על DB כדי להגן על ה-connection pool — HTTP עדיין טוען User מלא." |

---

## 14. שגיאות API אחידות (`LinkUpError`)

| | |
|--|--|
| **החלטה** | תתי-מחלקות דומיין (`RideNotFoundError`, …) + handlers גלובליים; `trace_id` מיושר ל-`request_id` מה-middleware. |
| **למה** | לקוחות ולוגים מקבלים `error_code` יציב; פחות `HTTPException` עם `detail` שרירותי ללוגיקה עסקית. |
| **מקור** | [../ERRORS.md](../ERRORS.md). |

---

## 15. AI לסיכום צ'אט (Groq)

| | |
|--|--|
| **החלטה** | **טריגר עליון בפועל:** משימות scheduled ב־**`task-worker`** ( למשל timeout שיחה) קוראות ל־`handle_conversation_completion` באותו monorepo — **Groq** → **`chat_analysis`** → Outbox. **בנוסף:** **`ai-worker`** מאזין ל־**`chat:completion:*`** (Redis DB חיבור הצ’אט) — פרסום מ-backend לערוץ זה **לא** אומת בקוד הנוכחי כמקור הטריגר היחיד. |
| **למה** | עומס הניתוח מחוץ ל-request path; פריסת workers נפרדת מ-Uvicorn; אפשרות הרחבה ל-Redis-trigger בעתיד. |
| **בקצרה לראיון** | "הניתוח רץ מתוך workers (timeout → `task-worker`), ויש מאזין ב-**`ai-worker`** לערוץ Redis אם נרצה decouple מלא מהמתזמן." |

---

## 16. מבדקי עומס (k6)

| | |
|--|--|
| **הקשר** | אימות auth, נסיעות, קבוצות, צ'אט HTTP, geo, WS תחת עומס. |
| **החלטה** | סקריפטים תחת `backend/k6/scripts/`; דורשים סביבה מוכנה (rate limits, DEBUG וכו'). |
| **למה** | לוודא שההחלטות (pool, rate limit, bcrypt) מתנהגות סבירות תחת מקביליות. |

---

## 17. חיפוש נוסע לעומת שמירת בקשה והתראה

| | |
|--|--|
| **הקשר** | נוסע רוצה לראות נסיעות זמינות בלי “לזהם” את ה-DB; וגם לקבל עדכון כשנהג מפרסם נסיעה חדשה שמתאימה. |
| **החלטה** | **חיפוש** — `GET /passenger/passengers/search-rides`: שאילתה בלבד (PostGIS / פילטרים), **ללא** `INSERT` ל-`passenger_requests`. **שמירה והתראה** — אותו מסלול כמו יצירת בקשה: `POST /passenger/passengers/` עם `PassengerRequestCreate` (`is_notification_active`, `group_id` אופציונלי). **שרשרת אסינכרונית לנוסעים:** ב-Outbox נרשם **`ride.created`** (לא שם אחר); `notification-worker` מפרסם ל-RabbitMQ ואז **`handle_ride_created`** טוען את הנסיעה, מריץ `find_passengers_for_ride_notification` (סינון: סטטוס פעיל, התראות פעילות, חלון תאריכים, התאמת `group_id` לנסיעה, קרבה גיאוגרפית ליעד ולמסלול), ולכל נוסע מתאים מפעיל את שכבת ההתראות עם אירוע הפנימי **`ride.created_for_passengers`** (מייל Brevo וכו’) — ראו `docs/architecture/EVENTS.md`. |
| **למה** | הפרדה בין “צפייה חד-פעמית” לבין מנוי לאירועים; מקור אמת אחד לבקשה (`passenger_requests`) גם להתאמות מיידיות (`matching_rides`) וגם לתור התראות. |
| **אלטרנטיבה** | לשמור כל חיפוש כ-row — עומס DB ורעש; או התראות בלי row — קשה לניהול ביטול והרשאות. |
| **בקצרה לראיון** | “חיפוש הוא read-only; רק POST יוצר בקשה שנכנסת לתזמורת ההתראות.” |

---

## 18. JWT — `jti` ו-denylist ב-Redis (ביטול access מיידי ב-logout)

| | |
|--|--|
| **הקשר** | Stateless JWT access קצר; רק ניקוי **refresh** ב-DB לא מבטל את ה-access הנוכחי עד לפקיעת `exp`. |
| **החלטה** | כל access token כולל **`jti`** (UUID). ב-**`POST /auth/logout`** עם **`Authorization: Bearer`** — אחרי ניקוי refresh, פענוח ה-access, חישוב **`TTL = max(0, int(exp − now))`** (שניות Unix), ו-**`SETEX denylist:{jti}`** ב-Redis DB0. ב-**`get_current_user`** / **`get_current_user_optional`** — אחרי `decode_access_token`, אם `jti` ב-denylist → 401 או `None`. |
| **Fail-open** | **`add_to_denylist`** — שגיאת Redis נרשמת, לא מפילה logout; **`is_denied`** — אם Redis לא זמין → **לא** חוסם (מעדיף זמינות על פני revocation קשיח בזמן תקלה). |
| **Trade-off** | בדיקת denylist ב-WS handshake מוסיפה תלות Redis במסלול החיבור; נשמר fail-open אם Redis לא זמין כדי לא לפגוע בזמינות כוללת. |
| **בקצרה לראיון** | “הוספתי `jti` וביטול מיידי דרך Redis כדי שלא נשאר access תקף אחרי logout — עם fail-open כדי לא לנעול משתמשים כש-Redis למטה.” |

---

## 19. Idempotency-Key — הצטרפות לנסיעה מחיפוש (`request-ride-from-search`)

| | |
|--|--|
| **הקשר** | לחיצה כפולה / retry רשת על **`POST …/passengers/request-ride-from-search`** עלולות ליצור שתי הזמנות לאותה נסיעה; **`BookingAlreadyExistsError`** לא מכסה כל מרוץ. |
| **החלטה** | כותרת אופציונלית **`Idempotency-Key`**; Redis **`SET NX`** על `idempotency:request_ride:{user_id}:{key}` לערך **`PROCESSING`**; SHA-256 של גוף קנוני ב־**`:fingerprint`**; אחרי **201** — שמירת JSON של **`BookingResponse`** (TTL ~5 דק׳); אותו מפתח + fingerprint → החזרת תשובה שמורה; בתהליך — **409** + **`Retry-After`**; fingerprint שונה — **422**; שגיאת דומיין — **`DELETE`** המפתחות לאפשר ניסוי חוזר. |
| **Stripe-style** | נשמרת רק **תשובת הצלחה**; שגיאות לא “ננעלות” כתוצאה זמינה. |
| **Fail-open** | Redis לא זמין → **`idempotency_try_begin`** מחזיר **`leader`** (אין dedup). |
| **פרונט** | **`requestRideFromSearch`** (`passengers.ts`) מקבל מפתח אופציונלי; **`useJoinRide`** שומר **`idempotencyKeyRef`** — UUID חדש לכל ניסיון הצטרפות, איפוס אחרי הצלחה, אותו מפתח ב-retry אחרי שגיאה; נקרא מ־**`useSearchRides`**. |
| **בקצרה לראיון** | “אותו דפוס כמו Stripe — `SET NX` + fingerprint + cache של 201 בלבד; בלי לשנות את לוגיקת **`BookingService.request_to_join`**.” |

---

## 20. Circuit Breaker — תלויות חיצוניות (Google Maps, Brevo email)

| | |
|--|--|
| **הקשר** | Geocoding / Directions / Distance Matrix וכן שליחת מייל transactional דרך **Brevo** הן תלויות רשת; תקלות, quota או שקט של הספק יכולות ליצור **סערת retries** (במיוחד עם Tenacity על ה-SDK של Brevo) ולהעמיס על workers והספק בו-זמנית. |
| **החלטה — מחלקה משותפת** | מימוש גנרי אחד ב־**`backend/app/infrastructure/circuit_breaker.py`**: **`CircuitBreaker`** מקבל **`state_gauge`** (Prometheus) ומעדכן לפי **`name`**. כך גיאו ו-Brevo לא משתפים מדד שגוי (`geo_*` לעומת `brevo_*`). |
| **גיאו** | Singletons ב־**`backend/app/infrastructure/geo/circuit_breaker.py`**: **`google_geocoding_cb`**, **`google_directions_cb`**, **`google_distance_matrix_cb`** עם **`geo_circuit_breaker_state`**. לפני כל קריאת HTTP — **`allow_request()`**; כש־**OPEN** — **אין** קריאה ל-Google (fail-fast: `None` / רשימה ריקה). |
| **Brevo** | Singleton **`brevo_email_cb`** ב־**`backend/app/infrastructure/notifications/circuit_breaker.py`** עם **`brevo_circuit_breaker_state`**. ב־**`EmailClient.send`**: אם **`allow_request()`** — מריצים את **`_send_with_retry`** (Tenacity פנימית); אם לא — **`EmailProviderCircuitOpenError`** (**503**, **`EMAIL_CIRCUIT_OPEN`**) **בלי** קריאה ל-Brevo. אחרי כל ניסיונות ה-retry — **`record_failure()`** פעם אחת לכשל לוגי; אחרי הצלחה — **`record_success()`**. **`ValueError`** על מפתח חסר — לפני המעגל (לא נספר ככשל ספק). |
| **פרמטרים** | אותם ברירות מחדל כמו גיאו: **5** כשלונות לפתיחה, **~60s** התאוששות (ניתן לכוונן ליד ה-singleton). |
| **חשיפת מצב** | **`GET /api/v1/health`** כולל **`circuit_breakers`** עם **`google_*`** ו־**`brevo_email`** — **מידע תפעולי בלבד**; **`status`** נקבע **רק** מ־**database**, **redis**, **rabbitmq**. |
| **Fail-open בתוך המעגל** | שגיאות פנימיות בלוגיקת המעגל (`allow_request` וכו’) במקרה קיצון מחזירות **להמשיך** או לבלוע שגיאה — העדפה לא לחסום את האפליקציה במלואה אם לוגיקת המעגל נכשלת (ראו קוד). |
| **בקצרה לראיון** | “יש מחלקת circuit breaker אחת עם gauge מוזרק; גיאו ו-Brevo עם singletons ומטריקות נפרדות; Brevo עטוף מבחוץ ו-Tenacity מבפנים כדי לא לספור כשל לכל retry ביניים.” |

---

## 21. PgBouncer — ממומש (Compose runtime)

| | |
|--|--|
| **הקשר** | עומסי burst/redeploy עם כמה services (backend + workers) יוצרים fan-out של חיבורים ל-Postgres. ב-EC2 בינוני זה מייצר לחץ מוקדם על memory/connection slots. |
| **החלטה** | להפעיל PgBouncer כ-layer פנימי ב-Compose במצב `transaction`, ולהעביר runtime services ל-`POSTGRES_HOST=pgbouncer` בעוד `migrate` נשאר direct ל-`db`. |
| **מימוש חשוב (ops)** | בגלל entrypoint overrides ב-images ציבוריים, ה-service משתמש ב-custom image (`infrastructure/pgbouncer/Dockerfile`) כדי לשמור שליטה מלאה על `pgbouncer.ini`. קובץ `userlist.txt` לא נשמר ב-git ולא נוצר על host/CI; הוא נוצר בתוך הקונטיינר בזמן startup מ־`userlist.txt.template` + env vars (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `PGBOUNCER_ADMIN_PASSWORD`) דרך `entrypoint.sh`. |
| **Trade-off** | עוד רכיב תפעולי ב-runtime (health/build/deploy ordering), אבל יציבות טובה יותר תחת עומס ו-rollout. |
| **בקצרה לראיון** | “לא הסתפקתי בלהוסיף PgBouncer — בניתי image מבוקר כדי למנוע entrypoint overrides, והקשחתי secrets flow כך שה-userlist נוצר בתוך הקונטיינר בזמן startup ולא תלוי בהרשאות host.” |

---

## 22. Chat input policy — plaintext-only (XSS hardening)

| | |
|--|--|
| **הקשר** | תוכן הודעות צ'אט נשמר ומופץ ללקוחות (REST + WS). גם אם ה־UI הנוכחי מרנדר טקסט, payload HTML שנשמר ב-DB עלול להוות סיכון לצרכנים עתידיים. |
| **החלטה** | בשכבת `MessageCreate` (קובץ `backend/app/domain/chat/schema.py`) מבוצעת בדיקה שמזהה תגיות HTML (`<...>`) ומחזירה שגיאת validation; הצ'אט מוגדר כ־**plaintext-only**. |
| **למה** | חסימה מוקדמת מונעת stored payloads בעייתיים בכל ה-pipeline; reject מפורש עדיף על strip שקט שיכול לשנות תוכן בלי שהמשתמש מבין. |
| **Trade-off** | טקסטים עם `<`/`>` בפורמט דמוי-תגית עשויים להידחות; זו החלטת מוצר מכוונת לטובת בטיחות ופשטות. |
| **בקצרה לראיון** | “בחרנו מדיניות צ'אט כטקסט בלבד ודחיית HTML בכניסה ל-API כדי לצמצם XSS across consumers.” |

---

## 23. Rate limiting — split by threat model (Sliding Window + Token Bucket)

| | |
|--|--|
| **הקשר** | מימוש קודם של rate limit ב-Redis היה fixed-window לא אטומי (`INCR` ואז `EXPIRE` בשתי פקודות). בגבול חלון ניתן להשיג burst של ~פי 2 מהמותר. בנוסף, אותו אלגוריתם שירת גם auth וגם chat למרות דרישות שונות. |
| **החלטה** | מעבר לשני Lua scripts אטומיים שונים: **`sliding_window`** ל-auth (פר-IP, ללא burst, anti-bruteforce), ו-**`token_bucket`** לצ'אט (פר-user, burst-tolerant). ה-scripts נרשמים דרך `redis-py register_script` (EVALSHA + fallback אוטומטי ל-EVAL על `NOSCRIPT`). |
| **למה** | **The right tool for the right threat**: ב-auth burst הוא בעיה אבטחתית ולכן Sliding Window. בצ'אט burst קצר הוא UX לגיטימי ולכן Token Bucket. בנוסף, אטומיות בלואה מבטלת race של fixed-window. |
| **API/Observability** | `RateLimitExceeded` הועשר לשדות `limit`, `remaining`, `retry_after`; handler מרכזי מחזיר `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`. נוספו מטריקות: `rate_limit_rejected_total{algorithm,endpoint}`, `rate_limit_redis_errors_total{endpoint}`, `rate_limit_evaluation_seconds{algorithm}`. |
| **Trade-off** | זמן `now_ms` מגיע מהאפליקציה ולא מ-`redis.call('TIME')` (NTP-bounded skew), וחישובי refill משתמשים ב-float של Lua 5.1. ב-scale הנוכחי זה טרייד-אוף סביר לטובת פשטות ותאימות רפליקציה. |
| **Fail-open** | כש-Redis לא זמין, הבקשה עוברת (זמינות עדיפה על חסימה גורפת של login/chat בזמן תקלת תשתית). האירוע נמדד ב-metrics. |
| **בקצרה לראיון** | “שדרגתי rate limiting מרמת ‘counter בחלון’ לרמה תפעולית-ארכיטקטונית: שני אלגוריתמים שונים לפי איום, אטומיות ב-Lua, headers סטנדרטיים ל-clients ומדדים שמאפשרים SLO אמיתי.” |

---

## 24. Persistent audit log for admin actions, billing webhook attempts, and auth events

| | |
|--|--|
| **הקשר** | אדמין מבצע פעולות רגישות (user active/admin toggle, ride cancel, outbox requeue), billing webhook יכול להישלח מחדש ע״י Stripe, ואירועי auth (login, logout, password change) דורשים forensic trail עצמאי מ-Prometheus metrics. לוגים בלבד לא מספיקים ל-forensics, ו-idempotency על `stripe_event_id` עלול להסתיר ניסיונות כפולים. |
| **החלטה** | טבלת `audit_log` append-only ב-Postgres + repository ייעודי לכתיבה/קריאה. ב-admin שומרים גם logger (`[admin_audit]`) וגם DB record (defense in depth). ב-`checkout.session.completed` רושמים audit attempt **לפני** בדיקת event-level idempotency כדי לתעד גם duplicate retries. **ב-auth router** רושמים `login` / `login_failed` / `logout` / `change_password` / `password_reset` עם IP מחולץ מ-`X-Forwarded-For` (shared helper `app.api.helpers.client_ip`). |
| **סכימה** | `audit_log(id, actor_user_id, action, resource_type, resource_id, metadata JSONB, ip_address, created_at)` + indexes לפי `(actor_user_id, created_at DESC)` ו-`(resource_type, resource_id)`. |
| **למה** | מחזק traceability, incident response ו-compliance בסיסי בלי תלות במערכת לוגים חיצונית בלבד. מאפשר feed אדמין מסונן לפי actor/resource/action עם limit. |
| **Trade-off** | תוספת write-path לכל פעולה רגישה ונפח metadata שעלול לגדול. mitigation: metadata קומפקטי בלבד; בלי payloadים מלאים. |
| **Fail policy** | ל-admin ול-billing נשמר best-effort pragmatic: כש-audit write נכשל — לוג warning, ולא שוברים את זרימת הדומיין הקריטית (במיוחד webhook processing). |
| **auth actions** | `login` (email/google success), `login_failed` (bad credentials / unverified / Google failure — metadata כולל `reason=error_code` + `provider`), `logout`, `change_password`, `password_reset` (OTP confirm). `resource_type="auth"` לכולם; `actor_user_id=NULL` כשהמשתמש לא מזוהה (failed login, unauthenticated reset). |
| **client_ip extraction** | `client_ip(request)` חולצה מ-`rate_limit.py` ל-`app/api/helpers.py` כ-shared utility — rate limiting ו-auth audit מייבאים ממודול אחד בלי שכפול קוד ובלי circular imports. |
| **בקצרה לראיון** | "תיעדתי פעולות רגישות בטבלת audit ייעודית — אדמין, billing, ועכשיו גם auth (login/logout/password). חילצתי `client_ip` ל-shared helper כדי ש-rate-limit ו-audit ישתמשו באותו מקור — בלי duplication." |

---

## 25. Idempotency-Key — שליחת הודעת צ’אט (`POST …/conversations/{id}/messages`)

| | |
|--|--|
| **הקשר** | לחיצה כפולה / retry רשת על שליחת הודעה עלולות ליצור שתי הודעות לוגיות לאותה שיחה. |
| **החלטה** | כותרת אופציונלית **`Idempotency-Key`**; מימוש מקביל ל-§19: Redis **`SET NX`** על `idempotency:chat_message:{user_id}:{key}` לערך **`PROCESSING`**; SHA-256 של גוף קנוני ב־**`:fingerprint`** (למשל `conversation_id` + תוכן הודעה); אחרי **201** — שמירת JSON של **`MessageResponse`** (TTL ~5 דק׳); אותו מפתח + fingerprint → תשובה שמורה; בתהליך — **409** + **`Retry-After`**; fingerprint שונה — **422**; שגיאת דומיין — **`DELETE`** המפתחות. קוד: **`backend/app/domain/chat/message_idempotency.py`**, wiring ב־**`chat/router.py`**. |
| **Stripe-style** | נשמרת רק **תשובת הצלחה** (201); שגיאות לא ננעלות כתוצאה זמינה. |
| **Fail-open** | Redis לא זמין → אין dedup (ממשיכים כמו לפני). |
| **פרונט** | **`sendMessage`** ב־**`frontend/src/api/chat.ts`** מוסיף **`Idempotency-Key`** (פרמטר אופציונלי; ברירת מחדל UUID אם לא הועבר). **זרימת UI:** **`useMessageThread`** / **`useChatPopup`** מעבירות מפתח יציב לניסיון שליחה (ref, כמו **`useJoinRide`**), מאפסות אחרי הצלחה, ועל **`idempotency_key_mismatch`** מנקות מפתח; רשימת הודעות מתעדכנת עם **`appendMessageDedupById`** (משותף לערוץ WS) — **`frontend/src/utils/`**. |
| **בקצרה לראיון** | “העתקתי את דפוס ה-idempotency של Stripe לצ’אט — נעילה פר-משתמש+מפתח, fingerprint, cache של 201 בלבד, בלי לשבור את לוגיקת השמירה בדומיין.” |

---

## 26. Billing — Postgres idempotency ל־`POST …/billing/checkout`, reconciler, ו-state machine לתשלום

| | |
|--|--|
| **הקשר** | Stripe Checkout נפתח מהדפדפן; retries ולחיצות כפולות על יצירת session; webhooks שנמשכים או חוזרים; צורך בעקביות מצב **`payments.status`** ו-**`users.is_premium`**. |
| **החלטה** | **`X-Idempotency-Key`** (כותרת) → טבלה **`idempotency_keys`** (משתמש+מפתח+endpoint ייחודיים, fingerprint SHA-256, **`response_body`** + **`status_code`**, **`expires_at`**). כפילות fingerprint — מחזירים תשובה שמורה; אי-התאמה — **`IDEMPOTENCY_MISMATCH`** (422). **`BillingReconciler`**: **`pg_try_advisory_lock`**, רשימת **`pending`** עם חלון גיל, **`stripe_gateway.retrieve_session`**, **`handle_checkout_completed`** / **`handle_session_expired`**, ניקוי idempotency שפג תוקף — מתוזמן ב-**`app/core/lifespan.py`** (`AsyncIOScheduler`, job `billing_reconciler`; כש־**`BILLING_RECONCILER_ENABLED`**). מעברי סטטוס: **`validate_transition`** — רק ממצב התחלתי מותר החוצה; **`ILLEGAL_PAYMENT_TRANSITION`** במעבר אסור. |
| **למה Postgres ל-checkout** | עמידות בין מופעי API וביטול תלות Redis לשכבה זו (בהשוואה לצ’אט/נסיעות — שם Redis אופטימלי ל-latency קצר ו-fail-open). |
| **Trade-off** | write נוסף למסד לכל checkout עם מפתח; reconciler = קריאות Stripe נוספות — מוגדרות חלון זמן ו-single-runner lock. |
| **מדדים** | **`billing_reconciler_runs_total`**, **`billing_reconciler_recovered_total`**, **`billing_reconciler_errors_total`**, **`billing_idempotency_hits_total`** — ראו **`docs/operations/MONITORING.md`**. |
| **בקצרה לראיון** | “אידמפוטנטיות של checkout ישבה ב-Postgres כדי לאחסן את תשובת השרת המלאה בין רפליקות; reconciler עם advisory lock מתקן פערים אם webhook מאחר, ומכונת מצבים חוסמת מעברים משוגעים בין סטטוסים.” |
| **פירוט מלא / הפניה** | [FEATURE_DECISIONS.md §billing-checkout-db-idempotency-reconciler](../FEATURE_DECISIONS.md#billing-checkout-db-idempotency-reconciler) · [API.md §Billing](../architecture/API.md) · מיגרציות ב-[DATABASE.md](../architecture/DATABASE.md) · [`backend/app/core/lifespan.py`](../../backend/app/core/lifespan.py) · [BILLING_REFACTOR_SUMMARY.md](../BILLING_REFACTOR_SUMMARY.md) — סיכום שמור במלואו (לפני/אחרי, טבלת Kafka) |

---

## 27. Production secret validation — `model_validator` for `SECRET_KEY`

| | |
|--|--|
| **הקשר** | `SECRET_KEY` משמש לחתימת JWT ואימות tokens. מפתח קצר בפרודקשן פוגע בביטחון כל מנגנוני ה-auth. |
| **החלטה** | `model_validator(mode="after")` ב-`Settings` (Pydantic v2 `BaseSettings`) מוודא ש-`SECRET_KEY` ≥ 32 תווים כש-`ENVIRONMENT=production`. |
| **למה `model_validator` ולא `field_validator`** | ב-Pydantic v2 עם `BaseSettings`, `field_validator(mode="after")` לא מקבל `info.data` עם שדות אחרים בצורה אמינה — הסדר תלוי בסדר ההגדרה במחלקה. `model_validator(mode="after")` רץ אחרי שכל השדות נטענו ומקבל `self` מלא. |
| **סקייל/תפעול** | אם `SECRET_KEY` בפרודקשן קצר מ-32 — `Settings()` זורק `ValueError` והאפליקציה לא עולה. ב-dev/staging אין אכיפה (ברירת מחדל `""` עובדת). |
| **בקצרה לראיון** | "הוספתי model_validator שמונע מהאפליקציה לעלות בפרודקשן עם מפתח JWT חלש — fail-fast בטעינה." |

---

## 28. Outbox MAX_RETRIES — retry cap for permanently failing events

| | |
|--|--|
| **הקשר** | אירוע outbox שנכשל שוב ושוב (למשל בגלל routing שגוי או exchange חסר) ממשיך לחזור ל-PENDING ומציף לוגים ו-metrics אינסופי. |
| **החלטה** | `MAX_RETRIES = 5` כקבוע ברמת מודול ב-`outbox_service.py`. בתחילת `process_single_event`, אם `retry_count >= MAX_RETRIES` — `mark_as_failed` (status=FAILED) + commit + `logger.error` + return. |
| **למה** | מניעת retry storms; אירועים שנכשלו לצמיתות מפסיקים לצרוך משאבי worker ו-DB. שחזור ידני אפשרי דרך ממשק האדמין (outbox requeue — מחזיר ל-PENDING). |
| **Trade-off** | `mark_as_failed` ב-repository מוסיף `retry_count + 1`, כך אירוע FAILED יציג `retry_count=6` — קוסמטי בלבד, לא משפיע על לוגיקה. |
| **בקצרה לראיון** | "הוספתי תקרת 5 ניסיונות ל-outbox כדי למנוע retry storms — FAILED events ניתנים לשחזור דרך אדמין." |

---

## 29. Transaction ownership — CRUD flush-only, caller commits

| | |
|--|--|
| **הקשר** | `CRUDUser` write methods (`update`, `update_location`, `update_fcm_token`, `update_refresh_token`, `update_password`, `mark_as_verified`, `update_last_active`) called `db.commit()` internally. This worked for simple operations but broke atomicity when callers needed to combine a DB write with an outbox event in a single transaction. Bug was first hit in `confirm_avatar_upload` and `remove_avatar` — fixed by bypassing CRUD, but the root cause remained. The same anti-pattern existed in **groups CRUD** — `create_group`, `join_group`, `remove_member`, `rename_group`, `update_group_description`, `update_group_avatar_key`, `close_group`, `update_member_role` all committed internally, making the `update_group` handler (rename + update description) non-atomic. |
| **החלטה** | All CRUD write methods use **`db.flush()`** only — they never commit. Callers own the transaction boundary and call **`await db.commit()`** when ready. One pattern, no `_no_commit` variants. Applied consistently across **users** and **groups** domains. |
| **מה השתנה** | **Users:** 7 methods in `users/crud.py` changed from `commit()` to `flush()`. 11 caller sites across 6 files (`auth/service.py` ×6, `push_provider.py` ×1, `users/service.py` ×2, `users/router.py` ×1, `chat/router.py` ×1) received explicit `await db.commit()`. Dead-code method `mark_as_verified` (zero callers) was removed. Two dedicated methods added: **`link_google_account`** and **`update_last_login`**. **Groups:** 8 methods in `groups/crud.py` changed from `commit()` to `flush()`. Commit ownership moved to `groups/service.py` (`create_group`, `join_by_invite`) and `groups/router.py` (7 write endpoints: `confirm_group_image`, `delete_group_image`, `remove_member`, `promote_member`, `leave_group`, `close_group`, `update_group`). Result: `update_group` (rename + update description) is now **atomic** — both operations commit together or roll back together. |
| **למה בטוח** | Session factory in [`app/db/session.py`](../../backend/app/db/session.py) sets **`expire_on_commit=False`** — ORM attributes remain accessible after commit without `refresh()`. Outbox `save_event` already uses `flush()`. Methods `create`, `mark_as_premium`, `update_stripe_customer_id` already followed this pattern with callers committing in `register_new_user`, `authenticate_with_google`, and `billing/service.py`. |
| **אלטרנטיבות** | (1) `_no_commit` variant methods — dual patterns, inconsistent, error-prone. (2) Context manager / middleware auto-commit — hides transaction boundaries, makes outbox atomicity implicit. |
| **סקייל** | Enables any future caller to combine DB writes + outbox events atomically without CRUD-layer changes. The pattern is now consistent across all domains (users, groups). |
| **בקצרה לראיון** | "העברתי transaction ownership מ-CRUD לקוראים — CRUD עושה flush בלבד, הקורא מחליט מתי לעשות commit. זה מאפשר atomicity בין כתיבות DB לאירועי outbox בלי band-aids. הדפוס חל גם על users וגם על groups." |

---

## 30. Automated PostgreSQL backup pipeline — pg_dump → encrypt → S3

| | |
|--|--|
| **הקשר** | PostgreSQL רץ על Docker named volume ב-EC2 יחיד. אין שום backup חיצוני — אובדן דיסק = אובדן כל הנתונים. |
| **החלטה** | Docker Compose service **`db-backup`** (profile `backup`) עם image מבוסס `postgres:15` + AWS CLI + `openssl`. Pipeline: `pg_dump --format=custom --compress=6` → AES-256-CBC encryption (`openssl enc`) → `aws s3 cp` → size verification. שני טריגרים: (1) cron יומי 03:00 UTC על host (`scripts/ops/setup-backup-cron.sh`), (2) pre-deploy hook ב-`deploy-ec2.yml` (non-blocking). S3 lifecycle: `daily/` → Glacier at 14d, expire 30d; `pre-deploy/` → Glacier 30d, expire 90d. |
| **למה pg_dump (ולא WAL-G)** | RPO מקובל (שעות) ל-MVP; logical dump = portable בין major versions; פחות מורכבות תפעולית; restore ל-RDS פשוט יותר (Phase 2). |
| **למה encryption** | Data-at-rest protection ב-S3; AES-256 עם passphrase ב-env var. מפתח חייב להישמר **בנפרד** מה-backups. |
| **למה pre-deploy** | Recovery point לפני כל migration — אם migration נכשלת, יש backup מיידי לחזרה. |
| **Restore** | `restore.sh` — S3 download → `openssl dec` → `pg_restore --clean --if-exists --no-owner`; `--list` mode למיפוי; post-restore row-count sanity check. |
| **Monitoring** | `scripts/ops/check-backup-health.sh` — freshness (<25h) + size threshold; exit code 1 on failure. |
| **Trade-offs** | RPO ~24h (daily) / ~deployment-interval (pre-deploy); restore time linear with DB size; encryption key = single point of recovery. |
| **Phase 2** | Migration ל-AWS RDS (managed PITR + automated snapshots) — `db-backup` pipeline נשמר ל-ad-hoc exports. |
| **בקצרה לראיון** | "זיהיתי SPOF על Postgres ב-EC2, הקמתי pipeline מוצפן ל-S3 עם שני טריגרים — יומי ולפני כל deploy. Phase 2 = RDS managed." |

---

## קישורים

- [README — מפת ADR](README.md)  
- [WEBSOCKETS.md](WEBSOCKETS.md) · [FCM_AND_PUSH.md](FCM_AND_PUSH.md)  
- [../ENGINEERING_HIGHLIGHTS.md](../ENGINEERING_HIGHLIGHTS.md) · [../architecture/EVENTS.md](../architecture/EVENTS.md)
