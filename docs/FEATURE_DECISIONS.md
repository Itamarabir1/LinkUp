# LinkUp — Feature Decisions (Why / Alternatives / Trade-offs)

מסמך **מקביל** ל-[ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md).  
**HIGHLIGHTS** = "מה בניתי + איפה בקוד". **מסמך זה** = להצגה בראיון: בעיה, החלטה, חלופות, מחיר, משפט פתיחה קצר.

> פירוט ADR מלא: [adr/ARCHITECTURE_DECISIONS_BACKEND.md](adr/ARCHITECTURE_DECISIONS_BACKEND.md) (§1–22) ו־[adr/ARCHITECTURE_DECISIONS_FRONTEND.md](adr/ARCHITECTURE_DECISIONS_FRONTEND.md), [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md).

---

<a id="outbox"></a>

## Outbox + RabbitMQ

| | |
|--|--|
| **בעיה** | אחרי `commit` ב-DB רוצים לאירוע חיצוני (מייל, FCM) — `publish` ישיר אחרי commit או אם הברוקר/שרת נופלים = אובדן או כפילות. |
| **החלטה** | שורה ב-`outbox_events` **באותה טרנזקציה** עם שינוי עסקי; worker מפרסם ל-RabbitMQ (LISTEN/NOTIFY + מנגנון fallback). |
| **אלטרנטיבות** | (1) Publish ישיר — פשוט אבל fragile. (2) Kafka — כבד יותר לסקייל נוכחי. (3) SQS — vendor lock, דורש מודל mental שונה. |
| **יתרון** | **at-least-once** + עקביות DB/אירוע; ה-API לא מחכה ל-latency של הברוקר. |
| **Trade-off** | צריך idempotency בצרכנים; מורכבות תפעול (worker + monitoring). |
| **Interview pitch (≈30s)** | *"יישמתי outbox: האירוע נשמר בטרנזקציה יחד עם הדאטה, אז אם הפרוסס קורס או Rabbit זמנית למטה — לא מאבדים. Worker מפרסם ל-Rabbit. המחיר הוא at-least-once אז בצרכנים בודקים idempotency."* |
| **הפניה** | ADR §4, HIGHLIGHTS §6, [architecture/EVENTS.md](architecture/EVENTS.md) |

---

<a id="chat-ws"></a>

## Real-time chat + chat-ws (Go)

| | |
|--|--|
| **בעיה** | הודעות 1:1 + typing + presence — צריך הרבה idle connections; לא רוצים לייבל את path ה-DB ב-Python. |
| **החלטה** | **Go `chat-ws`**: WebSocket, JWT ב-handshake, מנוי ל-**Redis** (`chat:conversation:*`, notification/typing, `user:*:events`), fan-out. Python שומר הודעה + publish ל-Redis. |
| **אלטרנטיבות** | (1) WebSocket ב-FastAPI בלבד — אפשרי אבל per-connection cost גבוה ב-Python. (2) SaaS (Pusher/Ably) — עלות+vendor. (3) רק long polling — גרוע ל-UX. |
| **יתרון** | הפרדת "מסע real-time" משכבת REST/DB; גורוטינים זולים per connection. |
| **Trade-off** | שני runtimes (Python + Go); אותו `SECRET_KEY` ל-WS. |
| **Interview pitch (≈30s)** | *"צ'אט: FastAPI שומר ב-Postgres ומפרסם ל-Redis, chat-ws ב-Go מנוי ודוחף ללקוח. בחרתי Go כי אלפי חיבורים idle זולים שם ולא שולפים load על SQLAlchemy."* |
| **הפניה** | [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md), HIGHLIGHTS §4, [architecture/REALTIME.md](architecture/REALTIME.md) |

---

<a id="chat-plaintext"></a>

## Chat: plaintext + דחיית HTML (XSS)

| | |
|--|--|
| **בעיה** | הודעות נשמרות ב-`messages.body`; אפשר לייצר **stored** payload (HTML) שישפיע עתידית על render או ייצוא. |
| **החלטה** | `MessageCreate` (Pydantic) — **דחייה** אם מזוהה תבנית תג HTML (`<...>`); הודעת שגיאה ברורה. מדיניות מוצר: **צ'אט = טקסט בלבד**. |
| **אלטרנטיבות** | (1) DOMPurify/escape בצד הלקוח בלבד — לא מספיק ל-API אחר. (2) Strip שקט — משנה תוכן בלי שקיפות. |
| **יתרון** | הכנסה "נקייה" ל-DB; עקבי לכל consumer (UI, אדמין עתידי, ייצוא). |
| **Trade-off** | טקסט לגיטימי עם `<`/`>` עלול להידחות; זו החלטת product. |
| **Interview pitch (≈30s)** | *"רינדור הודעה ב-React כבר בטוח כטקסט, אבל חיזקתי בשרת: הודעות שממלאות pattern של תג HTML נדחות, כי זה contract של plain text. זה שכבה נגד stored XSS, לא רק ref reflected."* |
| **הפניה** | ADR **§22**, [backend/app/domain/chat/schema.py](../backend/app/domain/chat/schema.py) |

---

<a id="chat-rate-limit"></a>

## Chat rate limit (per-user)

| | |
|--|--|
| **בעיה** | ספאם הודעות בצ'אט יוצר עומס כתיבה, רעש למשתמש השני וסיכון להתנהגות abuse. |
| **החלטה** | Dependency ייעודי `rate_limit_chat` בשכבת API: מפתח Redis פר-משתמש `ratelimit:chat:{user_id}`, חלון 60 שניות, מקסימום 30 הודעות לדקה ל-endpoint `POST /chat/conversations/{conversation_id}/messages`. |
| **אלטרנטיבות** | (1) Rate limit לפי IP בלבד — לא מדויק למשתמשים מאחורי NAT. (2) מנגנון throttling רק בפרונט — קל לעקיפה. (3) Queue עם slow mode — מורכב לדרישה הנוכחית. |
| **יתרון** | הגבלה הוגנת ברמת משתמש אותנטי, reuse מלא לתשתית `rate_limit_check` הקיימת, ללא שינוי בדומיין הצ'אט. |
| **Trade-off** | Redis למטה => fail-open לצורך זמינות (הגנה זמנית נחלשת). |
| **Interview pitch (≈30s)** | *"הוספתי rate limit פר-משתמש לשליחת הודעות בצ'אט, 30 לדקה. זה יושב כ-dependency ב-FastAPI ומשתמש באותה תשתית Redis של auth. בחרתי fail-open כדי לא לשבור זמינות אם Redis נופל."* |
| **הפניה** | [../backend/app/api/dependencies/rate_limit.py](../backend/app/api/dependencies/rate_limit.py), [../backend/app/domain/chat/router.py](../backend/app/domain/chat/router.py), [../ARCHITECTURE.md](../ARCHITECTURE.md) |

---

<a id="sentry"></a>

## Sentry — error monitoring (production)

| | |
|--|--|
| **בעיה** | שגיאות production אינן גלויות בזמן אמת — אי אפשר לאתר רגרסיות חדשות בלי לחפש ידנית בלוגים. |
| **החלטה** | Sentry SDK — backend: `sentry_sdk.init()` בתוך `setup_logging()` כש-`SENTRY_DSN` מוגדר (FastAPI/SQLAlchemy/Redis integrations, `traces_sample_rate=0.1`); `capture_exception` ל-5xx בלבד ב-`link_up_exception_handler`. Frontend: `Sentry.init()` ב-`main.tsx` (guard: `PROD + VITE_SENTRY_DSN`); `captureException` ב-axios interceptor (5xx), `ChatErrorBoundary`, `RouteErrorBoundary`. |
| **אלטרנטיבות** | (1) Rollbar / Datadog — אותו עיקרון, עלות גבוהה יותר. (2) Prometheus + Grafana — מדדים בלבד, אין stack traces. (3) לוגים בלבד — קשה לאתר רגרסיות בזמן אמת. |
| **יתרון** | stack traces מלאים עם `trace_id`; DSN לא נכנס ל-git (`.env` בלבד); fail-safe — אם Sentry down, השרת ממשיך. |
| **Trade-off** | capture ל-5xx בלבד מפחית רעש אבל עלול להחמיץ שגיאות לוגיקה שנבלעות או 4xx חריגים שתרצה לנטר בהמשך. |
| **Interview pitch (≈30s)** | *"הפעלתי Sentry: backend init ב-`logging.py` עם guard על `SENTRY_DSN`, capture רק ל-5xx כדי להפחית רעש. פרונט: init ב-`main.tsx` + שני error boundaries. DSN ב-`.env` בלבד — לא עולה ל-git."* |
| **הפניה** | [`../backend/app/core/logging.py`](../backend/app/core/logging.py), [`../backend/app/core/exceptions/handlers.py`](../backend/app/core/exceptions/handlers.py), [`../frontend/src/main.tsx`](../frontend/src/main.tsx) |

---

<a id="prometheus-grafana"></a>

## Prometheus + Grafana monitoring

| | |
|--|--|
| **בעיה** | `health` ולוגים עוזרים ל-diagnosis, אבל חסרים time-series metrics (RPS, latency, 5xx trend) ו-dashboard תפעולי רציף. |
| **החלטה** | `prometheus-fastapi-instrumentator` בבקאנד: חשיפת `/metrics` מ-`main.py`. ב-Compose נוספו שירותי `prometheus` ו-`grafana` תחת profile ייעודי `monitoring`, עם provisioning מוכן (`datasource + dashboard provider`) ו-dashboard בסיסי (`HTTP Requests/sec`, `p95`, `5xx`, `in-progress`). |
| **אלטרנטיבות** | (1) Datadog/NewRelic SaaS — מהיר יותר להתחלה אבל יקר יותר לסקייל וריבוי סביבות. (2) OpenTelemetry full stack — גמיש מאוד אך מורכב לשלב ראשון. (3) להישאר עם health+logs בלבד — פחות ראות מגמות. |
| **יתרון** | Visibility מיידי על ביצועי API, קל להרחיב ל-Redis/RabbitMQ/DB metrics בהמשך; profile `monitoring` שומר את סביבת dev קלה כשלא צריך observability stack. |
| **Trade-off** | Dashboard ראשוני ממוקד HTTP בלבד; queries תלויות naming של metrics מה-instrumentator ועלולות לדרוש התאמות לפי גרסה. |
| **Interview pitch (≈30s)** | *"הוספתי Prometheus ו-Grafana עם profile ייעודי ב-compose, וחשפתי `/metrics` בבקאנד. זה נותן baseline של RPS, p95, error rate ו-in-flight requests בלי להעמיס על סביבת פיתוח כשלא צריך."* |
| **הפניה** | [`../backend/app/main.py`](../backend/app/main.py), [`../docker-compose.yml`](../docker-compose.yml), [`../monitoring/prometheus.yml`](../monitoring/prometheus.yml), [`../monitoring/grafana/dashboards/linkup.json`](../monitoring/grafana/dashboards/linkup.json) |

---

<a id="chat-inbox-n1"></a>

## Chat inbox: batched aggregate (N+1 fix)

| | |
|--|--|
| **בעיה** | `list_my_conversations` קראה ל-`get_last_message` + `has_unread_messages` **לכל שיחה בנפרד** → 2N+ DB round-trips כשלמשתמש יש N שיחות. |
| **החלטה** | פונקציה חדשה `get_inbox_aggregates` ב-`chat/crud.py`: שלוש שאילתות מאוגדות (last message per conversation, last incoming per conversation, last_read_at per participant) + מיזוג בזיכרון. `list_my_conversations` קוראת לה פעם **אחת** ומייצרת את כל ה-`ConversationListItem`. |
| **אלטרנטיבות** | (1) `joinedload` ב-ORM — לא מספיק: לא מחשב `has_unread` ב-SQL. (2) GraphQL + DataLoader — overkill לממשק REST הנוכחי. (3) view materialised ב-Postgres — מורכבות תפעולית גבוהה, stale data. |
| **יתרון** | מ-~3N קריאות ל-**4 קריאות קבועות** ללא תלות בגודל ה-inbox; `get_last_message` + `has_unread_messages` המקוריות נשמרות לשימושים אחרים (DRY). |
| **Trade-off** | שאילתות ה-aggregate ארוכות יותר (subquery + join); אם inbox ריק — early return מיידי. |
| **Interview pitch (≈30s)** | *"ה-inbox הריץ get_last_message + has_unread לכל שיחה — N+1 קלאסי. החלפתי בפונקציה אחת שמריצה שלוש aggregate queries ומאחדת בזיכרון. מ-3N ל-4 קריאות קבועות, והפונקציות המקוריות נשמרות כי בשימוש במקומות אחרים."* |
| **הפניה** | [`../backend/app/domain/chat/crud.py`](../backend/app/domain/chat/crud.py) (`get_inbox_aggregates`), [`../backend/app/domain/chat/service.py`](../backend/app/domain/chat/service.py) (`list_my_conversations`) |

---

<a id="my-bookings"></a>

## My Bookings: aggregated reads (דילוג על N+1)

| | |
|--|--|
| **בעיה** | בטאב "הזמנות שלי" מספר קריאות per booking/ride יוצרות N+1 ו-UX איטי. |
| **החלטה** | Dedicate endpoints: `GET /bookings/driver-summary` ו-`GET /bookings/passenger-summary` + mapping ל-view-model; hooks מבודדים. |
| **אלטרנטיבות** | (1) GraphQL עם DataLoader. (2) BFF שמרכז. (3) N+1 עם `joinedload` — עדיין הרבה round-trips אם ה-UI שואל "פר booking". |
| **יתרון** | מעט round-trips, חוזה יציב ל-UI, קל לדגום ב-ראיון. |
| **Trade-off** | endpoints ייעודיים = יותר שטח API לתחזק. |
| **Interview pitch (≈30s)** | *"במקום שהפרונט יריץ N קריאות, הוספתי read models מרוכזים לנהג ולנוסע: טאב אחד = קריאה אחת, והמאפר מרכז את DTO→UI."* |
| **הפניה** | HIGHLIGHTS, `BookingReadsService`, [architecture/DATABASE.md](architecture/DATABASE.md) (אם רלוונטי) |

---

<a id="idempotency"></a>

## Idempotency-Key — `request-ride-from-search`

| | |
|--|--|
| **בעיה** | double tap / retry רשת → שתי bookings לאותו ride. |
| **החלטה** | Header אופציונלי, Redis `SET NX`, fingerprint לגוף, cache רק **201**; 409+Retry-After בזמן processing; **fail-open** בלי Redis. |
| **אלטרנטיבות** | (1) unique constraint DB בלבד — לא מכסה כל מרוץ. (2) idempotency רק בפרונט — לא אמין. |
| **יתרון** | אותו דפוס שמסחר אלקטרוני מכיר; לא שיניתי `BookingService.request_to_join` ללוגיקה, רק הכניסה. |
| **Trade-off** | בלי Redis אין dedup. |
| **Interview pitch (≈30s)** | *"Stripe-style: `SET NX` + fingerprint, שומרים רק תשובה מוצלחת. בלי Redis — fail-open כי זמינות מול dedup."* |
| **הפניה** | ADR §19, HIGHLIGHTS §7ה / 0א |

---

<a id="auth-session"></a>

## Auth: JWT + `jti` + denylist (logout)

| | |
|--|--|
| **בעיה** | JWT stateless — אחרי logout ה-access עדיין חתום עד `exp`. |
| **החלטה** | `jti` + `SETEX denylist:{jti}` ב-Redis עד `exp`; HTTP בודק; **fail-open** אם Redis down ב-read. |
| **אלטרנטיבות** | (1) session server-side (sticky). (2) רשימת ביטול ב-Postgres לכל request — עומס. (3) access קצר מאוד בלי denylist — UX גרוע. |
| **יתרון** | logout אמיתי על access בלי טבלת sessions גדולה. |
| **Trade-off** | בדיקות denylist בכל handshake מוסיפות תלות Redis במסלול WS auth; נבחר fail-open לשמירת זמינות אם Redis למטה. |
| **Interview pitch (≈30s)** | *"הוספתי jti ל-access ו-Redis denylist ב-logout גם ל-HTTP וגם ל-WS handshake. אם Redis נופל, בחרתי fail-open כדי לא ליפול גלובלית בזמינות."* |
| **הפניה** | ADR §18, HIGHLIGHTS §7ד |

---

<a id="circuit-breaker"></a>

## Circuit Breaker — Google Maps (באקאנד)

| | |
|--|--|
| **בעיה** | Geocoding/Directions איטי או 429 → storm של requests חוסמים workers. |
| **החלטה** | In-memory per-process circuit לכל API; OPEN = אין HTTP ל-Google; health מדווח `circuit_breakers` בלי לסמן את השרת unhealthy בגלל Google. |
| **אלטרנטיבות** | (1) Retry בלי cap — מחמיר. (2) rate limit בלבד. (3) sidecar (Envoy) — overkill. |
| **יתרון** | fail-fast; מגן על CPU ו-external budget. |
| **Trade-off** | מעגל **לא** משותף בין instances — reset אחרי deploy. |
| **Interview pitch (≈30s)** | *"לכל API של Google מעגל נפרד; אחרי סף כשלים נכנסים ל-OPEN — לא קוראים חיצונית, מחזירים שכבה ריקה. Health מציג מצב אבל status הכללי תלוי DB/Redis/Rabbit בלבד."* |
| **הפניה** | ADR §20, HIGHLIGHTS §0א |

---

<a id="email-renderer"></a>

## Email: React Email / Node `email-renderer`

| | |
|--|--|
| **בעיה** | Jinja2 מקומי ב-Python — קשה sharing עם פרונט, preview, קומפוננטות. |
| **החלטה** | מיקרו-שירות Node: `POST /render` { template, props } → HTML; Outbox/notification שולחים. |
| **אלטרנטיבות** | (1) MJML static. (2) שליחה דרך SaaS. (3) Jinja2 ב-Python. |
| **יתרון** | קומפוננטות, SSR כמו React, הפרדת אחריות. |
| **Trade-off** | hop רשת נוסף, health, סדר on compose. |
| **Interview pitch (≈30s)** | *"רינדור מייל עבר ל-Node+React Email — אותו mindset כמו SSR, templates ב-TS. ה-Python נשאר לאורקסטרציה ו-Outbox."* |
| **הפניה** | ADR §5, HIGHLIGHTS (מייל / email-renderer) |

---

<a id="fcm"></a>

## Push: FCM data-only

| | |
|--|--|
| **בעיה** | שליטה ב-UX: Toast בחזית, SW ברקע, עקביות בין iOS/Web. |
| **החלטה** | שרת שולח `data` map בלבד; קליינט מפרש ל-Toast/צליל. |
| **אלטרנטивות** | (1) `notification` object של FCM — פחות שליטה אחידה. |
| **יתרון** | שליטה מלאה בטקסט, שפה, A/B, analytics. |
| **Trade-off** | יותר לוגיקה בקליינט. |
| **הפניה** | [FCM_SYSTEM_SUMMARY.md](FCM_SYSTEM_SUMMARY.md), [adr/FCM_AND_PUSH.md](adr/FCM_AND_PUSH.md) |

---

## איך זה יושב מול High ו־ADR

- **השתמש ב-FEATURE_DECISIONS** כששואלים: *"למה לא X?"* — עמודת **אלטרנטיבות** + **Trade-off**.
- **השתמש ב-ENGINEERING_HIGHLIGHTS** לקישור לנתיבי קבצים ומספור סעיפים.
- **השתמש ב-ADR** כששואלים deep dive (מספור §).

[← חזרה ל-Interview Playbook](INTERVIEW_PLAYBOOK.md)

---

<a id="pgbouncer"></a>

## PgBouncer (EC2 + Docker Compose)

| | |
|--|--|
| **בעיה** | כמה services (backend + workers) עם pools נפרדים יוצרים fan-out לחיבורי Postgres תחת עומס/redeploy. ב-EC2 בינוני זה פוגע בזיכרון/latency לפני CPU saturation. |
| **החלטה** | להוסיף `pgbouncer` כ-service פנימי ב-Compose (transaction mode), ולהעביר runtime services ל-`POSTGRES_HOST=pgbouncer`. |
| **אלטרנטיבות** | (1) להגדיל רק `max_connections` ב-Postgres — מטפל סימפטום ולא שורש. (2) בלי pooler, רק להקטין `DB_POOL_*` — עוזר חלקית. (3) RDS Proxy/managed pooler — עדיף בענן מנוהל אבל לא quickest win ב-EC2 קיים. |
| **מה סניור עושה (לא טריוויאלי)** | (1) `migrate` נשאר direct ל-`db` ולא דרך pooler. (2) asyncpg statement cache מנוטרל (`statement_cache_size=0`) לתאימות transaction pooling. (3) PgBouncer internal-only בלי פתיחת `6432` לציבור. (4) right-size ל-SQLAlchemy pools כדי להימנע מ-double-pooling אגרסיבי. |
| **יתרון** | connection storms נבלמים מוקדם, יותר יציבות בזמן deploys, ו-headroom להמשך scaling בלי שינוי לוגיקה דומיינית. |
| **Trade-off** | עוד רכיב תפעולי לנטר (health/config/auth), וצריך משמעת סביב סודות `userlist` + smoke checks בפריסה. |
| **Interview pitch (≈30s)** | *"במקום שכל service יפציץ את Postgres בחיבורים, הוספתי PgBouncer כ-layer פנימי. השארתי migrations direct ל-db, כיביתי statement cache ב-asyncpg, והקטנתי pools אפליקטיביים — זה בדיוק ההבדל בין 'להוסיף container' לבין rollout יציב ברמת production."* |
| **הפניה** | `docker-compose.yml`, `backend/app/db/session.py`, `infrastructure/pgbouncer/pgbouncer.ini`, `scripts/ops/pgbouncer-smoke.sh` |

---

<a id="redis-sentinel"></a>

## Redis Sentinel HA (EC2 + Docker Compose)

| | |
|--|--|
| **בעיה** | Redis single-node הוא SPOF: נפילה/ריסטארט בזמן אמת שוברת cache, denylist, idempotency, ו-pub/sub לצ'אט עד התאוששות ידנית. |
| **החלטה** | לעבור לטופולוגיית `redis-primary` + `redis-replica` + `redis-sentinel`, עם clients Sentinel-aware ב-Python (`redis.asyncio.Sentinel`) וב-Go (`go-redis` failover). |
| **אלטרנטיבות** | (1) ElastiCache/Managed Redis — עדיף בפרודקשן מנוהל אבל לא תמיד זמין מיד תקציבית. (2) Redis Cluster — מורכב יותר מהצורך הנוכחי (שימוש כ-key/value + pub/sub). (3) להישאר single-node עם restart policy — לא פותר failover אמיתי. |
| **מה סניור עושה (לא טריוויאלי)** | (1) שומר `REDIS_HOST=redis` כ-alias ל-master כדי לא לשבור קונפיג קיים. (2) מוסיף fallback ל-URL רגיל ללוקאל/dev. (3) מחליף `broadcaster` ב-adapter פנימי ששומר API זהה לראוטרים (`event.message`). (4) ב-`subscribe()` מבצע cleanup שקט על `WebSocketDisconnect` בלי לדלוף pubsub handles. |
| **יתרון** | זמינות גבוהה יותר ל-real-time ו-state infra בלי שינוי בדומיין העסקי; failover שקוף יחסית לאפליקציה. |
| **Trade-off** | יותר מורכבות תפעולית (3 שירותי Redis, smoke checks, observability), ו-footprint גדול יותר על EC2 קטן. |
| **Interview pitch (≈30s)** | *"העברתי את Redis מ-single instance ל-Sentinel HA. השארתי alias `redis` כדי לא לשבור env קיים, הוספתי Sentinel-aware clients ב-Python וב-Go, והחלפתי broadcaster ב-adapter פנימי עם אותו חוזה לראוטרים. התוצאה: failover תפעולי בלי לגעת ב-domain logic."* |
| **הפניה** | `docker-compose.yml`, `infrastructure/redis/sentinel.conf`, `backend/app/infrastructure/redis/{client.py,chat_pubsub.py,broadcast.py}`, `chat-ws/cmd/server/main.go`, `scripts/ops/redis-sentinel-smoke.sh` |
