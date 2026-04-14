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
| **החלטה** | כתיבת שורה ל-`outbox_events` **באותה טרנזקציה** עם השינוי העסקי; `outbox-worker` מושך PENDING ומפרסם ל-RabbitMQ. |
| **למה** | **At-least-once**; ה-API לא תלוי ב-latency או זמינות הברוקר בזמן התשובה ללקוח. |
| **אלטרנטיבה** | Publish ישיר אחרי commit — race/crash עלולים לאבד אירוע. |
| **בקצרה לראיון** | "אאוטבוקס מבטיח שהאירוע והנתונים ב-DB יהיו עקביים — זה דפוס מוכר במערכות event-driven." |

---

## 5. תזמון (scheduled work)

## 4א. Email rendering service (React Email, Node.js)

| | |
|--|--|
| **הקשר** | רינדור מיילים בוצע מקומית ב-Jinja2 בתוך הבקאנד; נדרש מעבר לתבניות מודרניות, רכיבים משותפים ו-preview נוח. |
| **החלטה** | מיקרו-שירות `email-renderer` (Node.js + Express + React Email) אחראי על רינדור HTML. הבקאנד/worker שולחים `template + props` ל-`POST /render`. |
| **למה (סקייל)** | הפרדת אחריות: orchestration ושליחה נשארים ב-Python (Outbox/worker), rendering מרוכז בשירות ייעודי שניתן להרחיב ולעדכן בנפרד. |
| **חוזה** | `EMAIL_MAP` בבקאנד משתמש ב-template names ב-**PascalCase**; ב-renderer יש `TEMPLATE_REGISTRY` + fail-fast validation מול `EMAIL_MAP_KEYS` בזמן startup. |
| **Trade-off** | תלות רשת נוספת (timeout/health/startup ordering). ב-Compose הוגדר healthcheck ו-`depends_on` ל-`email-renderer` עבור `backend` ו-`outbox-worker`. |
| **בקצרה לראיון** | "הפרדנו רינדור מייל לשירות Node עם React Email; הבקאנד נשאר אחראי לאירועים ושליחה אמינה דרך Outbox." |

---

## 5. תזמון (scheduled work)

| | |
|--|--|
| **הקשר** | תזכורות נסיעה, תחזוקה, timeout לצ'אט, סריקת דלק. |
| **החלטה** | לולאת **publisher** קלה ב-worker (~**60 שניות**) שבודקת "הגיע הזמן" ודוחפת routing keys ל-exchange `scheduled`; הלוגיקה הכבידה רצה ב-**consumer** של `scheduled_tasks_queue`. מרווחים אופייניים: תזכורות ~**5 דקות**, תחזוקה ~**25 דקות**, chat timeout ~**שעה**, דלק ~**יומי** (ראו `docs/ENGINEERING_HIGHLIGHTS.md` סעיף 2א). |
| **למה** | הפרדה בין "מתזמן דק" לבין "עובד כבד" — קל להרחבה, לוגים וניטור. תזכורות מבוססות טבלת **`scheduled_notifications`** (מיגרציה 008) במקום דגלי `reminder_sent` על rides/bookings — מקור אמת אחד לתזמון. |
| **בקצרה לראיון** | "לא רצינו cron אחד ענק; דוחפים משימות לתור וה-worker המאוחד מבצע." |

---

## 6. Python, FastAPI, async SQLAlchemy

| | |
|--|--|
| **החלטה** | API ב-**FastAPI**; גישה ל-DB ב-**async** SQLAlchemy 2.0 בדומיינים ליבה (passengers, bookings, rides); workers רצים מתוך אותו codebase (`outbox-worker`). |
| **למה** | מהירות פיתוח, אקוסיסטם; async מתאים ל-I/O כבד (DB, HTTP חיצוני) תחת עומס. |
| **סקייל** | אין `Session.run_sync` בזרימות אפליקציה — רק Alembic; workers עם `await db.execute(select(...))` במקום חסימות מיותרות. |
| **בקצרה לראיון** | "Python ללוגיקה עסקית ואינטגרציות; async כדי לא לחסום את ה-event loop על DB." |

---

## 7. Uvicorn workers ו-connection pool ל-Postgres

| | |
|--|--|
| **החלטה** | מספר workers לפי `UVICORN_WORKERS` (Docker); `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `pool_pre_ping` מ-config. |
| **למה (סקייל)** | יותר workers = יותר בקשות מקביליות, אבל כל worker משתמש בחיבורי pool — צריך איזון מול מגבלות Postgres. **`pool_pre_ping`** מפחית כשלי חיבור מתים אחרי recycle של השרת. |
| **בקצרה לראיון** | "מגדילים replicas ו-workers בזהירות מול גודל ה-pool — זה trade-off קלאסי." |

---

## 8. נעילות ורaces (הזמנות)

| | |
|--|--|
| **החלטה** | `SELECT ... FOR UPDATE` על נסיעה באישור/ביטול הזמנה; התראות ביטול נסיעה רק לבוקינגים ב-**PENDING** או **CONFIRMED**. |
| **למה** | מניעת race conditions תחת בקשות מקביליות; פחות "רעש" והתראות שגויות. |
| **בקצרה לראיון** | "נעילה פסימית היכן שיש תחרות על אותה נסיעה." |

---

## 9. Cursor pagination

| | |
|--|--|
| **החלטה** | חיפוש נסיעות והודעות צ'אט עם `after` / `before` + `limit`, לא offset גדול בלבד. |
| **למה (סקייל)** | Offset עמוק על טבלאות גדולות יקר; cursor יציב יותר תחת נתונים שגדלים. |
| **בקצרה לראיון** | "Cursor pagination לרשימות שיכולות לגדול מאוד." |

---

## 10. S3 ו-CloudFront (אופציונלי)

| | |
|--|--|
| **החלטה** | העלאות עם **presigned PUT**; אווטאר משתמש ב-prefix **גרסתי** `avatars/{user_id}/v{version}/`; מחיקת גרסה קודמת ב-S3 אחרי commit ל-DB. קריאה: אם מוגדר **`CLOUDFRONT_DOMAIN`** — URL ציבורי יציב; אחרת presigned GET. |
| **למה** | ה-API לא מזרים bytes של תמונות; CDN מפחית עומס על ה-API ומאפשר caching בצד CDN. |
| **בקצרה לראיון** | "אחסון אובייקטים ב-S3, חתימה לזמן קצר או CloudFront ליציבות URL." |

---

## 11. אבטחה ועומס (auth)

| | |
|--|--|
| **החלטה** | bcrypt דרך **thread pool** (`run_in_executor`) כדי לא לחסום event loop; rate limit על register/login (Redis); OTP עם `secrets` + `hmac.compare_digest`; לוגין עם **אותה תגובת שגיאה** לאימייל לא קיים ולסיסמה שגויה (מניעת user enumeration). |
| **למה** | תחת הרשמות/לוגין מקביליים bcrypt עלול לרסן את כל ה-API אם רץ על הלולאה הראשית. |
| **בקצרה לראיון** | "הפרדנו CPU כבד של סיסמאות ל-thread pool כדי לשמור על רספונסיביות של ה-API." |

---

## 12. WebSocket על FastAPI — JWT בלי DB ב-handshake

| | |
|--|--|
| **הקשר** | WS לנסיעות, מיקום, פיד התראות in-app. |
| **החלטה** | `get_current_user_ws` מאמת **רק JWT** ומחזיר `WsUser` — **בלי SELECT ל-DB** בזמן החיבור. |
| **למה (סקייל)** | אלפי חיבורי WS פותחים לא מציפים את pool ה-DB; trade-off: לא בודקים `is_active` ב-handshake עד פקיעת הטוקן. |
| **פירוט מלא** | [WEBSOCKETS.md](WEBSOCKETS.md). |
| **בקצרה לראיון** | "בחיבור WS דילגנו על DB כדי להגן על ה-connection pool — HTTP עדיין טוען User מלא." |

---

## 13. שגיאות API אחידות (`LinkupError`)

| | |
|--|--|
| **החלטה** | תתי-מחלקות דומיין (`RideNotFoundError`, …) + handlers גלובליים; `trace_id` מיושר ל-`request_id` מה-middleware. |
| **למה** | לקוחות ולוגים מקבלים `error_code` יציב; פחות `HTTPException` עם `detail` שרירותי ללוגיקה עסקית. |
| **מקור** | [../ERRORS.md](../ERRORS.md). |

---

## 14. AI לסיכום צ'אט (Groq)

| | |
|--|--|
| **החלטה** | אירוע סיום שיחה → Redis DB1 (`chat:completion:*`) → **אותו outbox-worker** מאזין ומריץ ניתוח, שומר ל-DB; לא microservice נפרד בפריסה הראשונית. |
| **למה** | פחות רכיבים לפרוס ולנטר; עדיין ביצוע אסינכרוני אחרי סגירת השיחה. |
| **בקצרה לראיון** | "שמרנו על משטח פריסה קטן — ה-worker כבר רץ ומאזין ל-Redis." |

---

## 15. מבדקי עומס (k6)

| | |
|--|--|
| **הקשר** | אימות auth, נסיעות, קבוצות, צ'אט HTTP, geo, WS תחת עומס. |
| **החלטה** | סקריפטים תחת `backend/k6/scripts/`; דורשים סביבה מוכנה (rate limits, DEBUG וכו'). |
| **למה** | לוודא שההחלטות (pool, rate limit, bcrypt) מתנהגות סבירות תחת מקביליות. |

---

## 16. חיפוש נוסע לעומת שמירת בקשה והתראה

| | |
|--|--|
| **הקשר** | נוסע רוצה לראות נסיעות זמינות בלי “לזהם” את ה-DB; וגם לקבל עדכון כשנהג מפרסם נסיעה חדשה שמתאימה. |
| **החלטה** | **חיפוש** — `GET /passenger/passengers/search-rides`: שאילתה בלבד (PostGIS / פילטרים), **ללא** `INSERT` ל-`passenger_requests`. **שמירה והתראה** — אותו מסלול כמו יצירת בקשה: `POST /passenger/passengers/` עם `PassengerRequestCreate` (`is_notification_active`, `group_id` אופציונלי). Worker על אירוע יצירת נסיעה קורא ל-`find_passengers_for_ride_notification` ומדלג על בקשות עם `is_notification_active=False` ועל אי-התאמת קבוצה. |
| **למה** | הפרדה בין “צפייה חד-פעמית” לבין מנוי לאירועים; מקור אמת אחד לבקשה (`passenger_requests`) גם להתאמות מיידיות (`matching_rides`) וגם לתור התראות. |
| **אלטרנטיבה** | לשמור כל חיפוש כ-row — עומס DB ורעש; או התראות בלי row — קשה לניהול ביטול והרשאות. |
| **בקצרה לראיון** | “חיפוש הוא read-only; רק POST יוצר בקשה שנכנסת לתזמורת ההתראות.” |

---

## קישורים

- [README — מפת ADR](README.md)  
- [WEBSOCKETS.md](WEBSOCKETS.md) · [FCM_AND_PUSH.md](FCM_AND_PUSH.md)  
- [../ENGINEERING_HIGHLIGHTS.md](../ENGINEERING_HIGHLIGHTS.md) · [../architecture/EVENTS.md](../architecture/EVENTS.md)
