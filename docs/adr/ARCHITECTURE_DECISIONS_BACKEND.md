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

---

## 5. רינדור מיילים — שירות Node.js (Express, React Email)

| | |
|--|--|
| **הקשר** | רינדור מיילים בוצע מקומית ב-Jinja2 בתוך הבקאנד; נדרש מעבר לתבניות מודרניות, רכיבים משותפים עם הפרונט ו-preview נוח. |
| **החלטה** | מיקרו-שירות **`email-renderer`** (Node.js + TypeScript + Express + React / `@react-email/components`) מחזיר HTML; הבקאנד וה-`outbox-worker` שולחים `template + props` ל-**`POST /render`**. |
| **למה Node.js** | תבניות מבוססות **React Email** נרנדרות בשרת עם **`renderToStaticMarkup`** — אותו דפוס כמו SSR בדפדפן, בלי להטמיע מנוע JavaScript בתוך תהליך Python; TypeScript וכלים (`react-email`) מיושרים לצוות הפרונט. |
| **למה (סקייל / תפעול)** | **הפרדת אחריות**: orchestration, Outbox ושליחת SMTP נשארים ב-Python; רינדור HTML מרוכז בשירות שניתן לסקייל, לגרסאות ולפריסה עצמאית. |
| **חוזה** | `EMAIL_MAP` בבקאנד משתמש ב-template names ב-**PascalCase**; ב-renderer יש `TEMPLATE_REGISTRY` + אימות fail-fast מול `EMAIL_MAP_KEYS` בזמן startup. |
| **Trade-off** | תלות רשת נוספת (timeout, health, סדר עלייה). ב-Docker Compose: **healthcheck** ו-**`depends_on`** מ-`email-renderer` ל-`backend` ול-`outbox-worker`. |
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
| **החלטה** | API ב-**FastAPI**; גישה ל-DB ב-**async** SQLAlchemy 2.0 בדומיינים ליבה (passengers, bookings, rides); workers רצים מתוך אותו codebase (`outbox-worker`). |
| **למה** | מהירות פיתוח, אקוסיסטם; async מתאים ל-I/O כבד (DB, HTTP חיצוני) תחת עומס. |
| **סקייל** | אין `Session.run_sync` בזרימות אפליקציה — רק Alembic; workers עם `await db.execute(select(...))` במקום חסימות מיותרות. |
| **בקצרה לראיון** | "Python ללוגיקה עסקית ואינטגרציות; async כדי לא לחסום את ה-event loop על DB." |

---

## 8. Uvicorn workers ו-connection pool ל-Postgres

| | |
|--|--|
| **החלטה** | מספר workers לפי `UVICORN_WORKERS` (Docker); `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `pool_pre_ping` מ-config. |
| **למה (סקייל)** | יותר workers = יותר בקשות מקביליות, אבל כל worker משתמש בחיבורי pool — צריך איזון מול מגבלות Postgres. **`pool_pre_ping`** מפחית כשלי חיבור מתים אחרי recycle של השרת. |
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
| **החלטה** | אירוע סיום שיחה → Redis DB1 (`chat:completion:*`) → **אותו outbox-worker** מאזין ומריץ ניתוח, שומר ל-DB; לא microservice נפרד בפריסה הראשונית. |
| **למה** | פחות רכיבים לפרוס ולנטר; עדיין ביצוע אסינכרוני אחרי סגירת השיחה. |
| **בקצרה לראיון** | "שמרנו על משטח פריסה קטן — ה-worker כבר רץ ומאזין ל-Redis." |

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
| **Trade-off** | WebSocket (`get_current_user_ws`) — **עדיין לא** בודק denylist (TODO); חיבורים קיימים תקפים עד פקיעת JWT. |
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

## 20. Circuit Breaker — קריאות Google Maps Platform בבקאנד

| | |
|--|--|
| **הקשר** | Geocoding, Directions ו-Distance Matrix הם תלות חיצונית; תקלות ברשת, בצד Google או quota יכולות ליצור **סערת retries** ולהעמיס על ה-API והספק בו-זמנית. |
| **החלטה** | שלושה **singletons** in-memory ב־**`backend/app/infrastructure/geo/circuit_breaker.py`**: **`google_geocoding_cb`**, **`google_directions_cb`**, **`google_distance_matrix_cb`**. לפני כל קריאת HTTP מתאימה — **`allow_request()`**; הצלחה/כשל מעדכנים את המעגל (**CLOSED → OPEN** אחרי **5** כשלונות רצופים; **OPEN → HALF_OPEN** אחרי **~60 שניות** התאוששות; חזרה ל-**CLOSED** אחרי בקשה מוצלחת). כשהמעגל **OPEN** — **אין** קריאה ל-Google (fail-fast: `None` / רשימה ריקה לפי הזרימה). |
| **חשיפת מצב** | **`GET /api/v1/health`** כולל **`circuit_breakers`** עם שמות המצבים — **מידע תפעולי בלבד**; **`status`** (`healthy` / `unhealthy`) נקבע **רק** מ־**database**, **redis**, **rabbitmq** כדי שלא יסומן ה-backend כלא-זמין רק בגלל Google. |
| **Fail-open בתוך המעגל** | שגיאות פנימיות בלוגיקת המעגל (`allow_request` וכו’) במקרה קיצון מחזירות **להמשיך** או לבלוע שגיאה — העדפה לא לחסום את האפליקציה במלואה אם לוגיקת המעגל נכשלת (ראו קוד). |
| **בקצרה לראיון** | “עטפתי את שלוש קריאות ה-Maps בבקאנד במעגלים נפרדים — כשהספק נופל, אני נכשל מהר ולא מציף את Google; את מצב המעגל רואים ב-health בלי לשבור readiness של השרת.” |

---

## 21. PgBouncer — מתוכנן (לא ממומש בפרויקט)

| | |
|--|--|
| **הקשר** | כשמספר מופעי API גדל (למשל **10+**) או פריסה serverless-ית, כל מופע פותח חיבורי SQLAlchemy ל-PostgreSQL — סכום מהיר של חיבורים פיזיים. |
| **החלטה (עתידית)** | להציב **PgBouncer** (או pooler דומה) בין האפליקציה ל-DB, לרכז אלפי חיבורי לקוח לפחות חיבורים לשרת Postgres. |
| **מצב נוכחי** | **אין** PgBouncer ב-Compose או ב-K8s בקוד הבסיס; **SQLAlchemy async pool** (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, …) + מספר workers (`UVICORN_WORKERS`) — Postgres נוח בטווח של **מאות** חיבורים עם tuning. |
| **למה לא עכשיו** | עלות תפעול ומורכבות; לסקלה הנוכחית ה-pool המקומי מספיק. |
| **בקצרה לראיון** | “כשאעלה לריבוי מופעים אגרסיבי, אוסיף PgBouncer; היום ה-pool של SQLAlchemy ומגבלות worker מכסים.” |

---

## קישורים

- [README — מפת ADR](README.md)  
- [WEBSOCKETS.md](WEBSOCKETS.md) · [FCM_AND_PUSH.md](FCM_AND_PUSH.md)  
- [../ENGINEERING_HIGHLIGHTS.md](../ENGINEERING_HIGHLIGHTS.md) · [../architecture/EVENTS.md](../architecture/EVENTS.md)
