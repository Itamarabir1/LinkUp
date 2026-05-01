# LinkUp — Feature Decisions (Why / Alternatives / Trade-offs)

מסמך **מקביל** ל-[ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md).  
**HIGHLIGHTS** = "מה בניתי + איפה בקוד". **מסמך זה** = להצגה בראיון: בעיה, החלטה, חלופות, מחיר, משפט פתיחה קצר.

> פירוט ADR מלא: [adr/ARCHITECTURE_DECISIONS_BACKEND.md](adr/ARCHITECTURE_DECISIONS_BACKEND.md) (§1–25) ו־[adr/ARCHITECTURE_DECISIONS_FRONTEND.md](adr/ARCHITECTURE_DECISIONS_FRONTEND.md), [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md).

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

<a id="rabbitmq-pr1-pr2"></a>

## RabbitMQ reliability refactor (PR1 + PR2)

| | |
|--|--|
| **בעיה** | consumer loop בודד + channel משותף לכל flows יצרו סיכון ל-crash loops שקטים ול-backpressure בין consume/publish. |
| **החלטה** | PR1: supervision עם draining states ו-`max_retries` ל-loopים ארוכי חיים. PR2: הפרדת clients לפי תפקיד (`rabbit_client`, `outbox_rabbit_client`, `worker_rabbit_client`) + channel isolation לכל queue + `QueueSpec` מרכזי לטופולוגיה. |
| **אלטרנטיבות** | (1) להשאיר singleton channel ולתקן נקודתית חריגות. (2) חיבור נפרד לכל worker/task — אמין אבל כבד מדי ל-`t3.medium`. |
| **יתרון** | בידוד עומסים בין publish/consume, recovery יותר צפוי, ויכולת לנהל policy ברמת queue ממקור אמת אחד. |
| **Trade-off** | יותר שכבת infra וקונפיגורציה; דורש משמעת תיעוד כדי לשמור sync בין topology לקוד worker. |
| **Interview pitch (≈30s)** | *"ב-PR1 הוספתי supervision ודראינינג כדי למנוע task death שקט. ב-PR2 פיצלתי נתיבי RabbitMQ לפי תפקידים והעברתי queue policies ל-QueueSpec מרכזי. כך צמצמתי coupling בין consumers ו-publishers בלי להוסיף תשתית ענן חדשה."* |
| **הפניה** | `backend/app/infrastructure/rabbitmq/{client.py,consumer.py,supervisor.py,topology.py}`, `architecture/EVENTS.md`, `ENGINEERING_HIGHLIGHTS.md` |

---

<a id="chat-ws"></a>

## Real-time chat + chat-ws (Go)

| | |
|--|--|
| **בעיה** | הודעות 1:1 + typing + presence — צריך הרבה idle connections; לא רוצים לייבל את path ה-DB ב-Python. |
| **החלטה** | **Go `chat-ws`**: WebSocket, JWT ב-handshake, מנוי ל-**Redis** (`chat:conversation:*`, notification/typing, `user:*:events`), fan-out. Python שומר הודעה + publish ל-Redis. במסלול הנכנס: **`SetReadLimit(2048)`** על המסר; דילול **פרסום `typing_*` לרדיס** פר־חיבור עם **`x/time/rate`** (**`ping`** פטור). **מסגרות WS יוצאות** יכולות לאחות כמה JSONים עם newline — הפרונט מפצל לפני parse (**`useUserEventStream`**); **`message_read`** דורש **`recipient_id`** ב-payload כדי לנתב עדכוני read receipt חיים לשולח. |
| **אלטרנטיבות** | (1) WebSocket ב-FastAPI בלבד — אפשרי אבל per-connection cost גבוה ב-Python. (2) SaaS (Pusher/Ably) — עלות+vendor. (3) רק long polling — גרוע ל-UX. |
| **יתרון** | הפרדת "מסע real-time" משכבת REST/DB; גורוטינים זולים per connection. |
| **Trade-off** | שני runtimes (Python + Go); אותו `SECRET_KEY` ל-WS. |
| **Interview pitch (≈30s)** | *"צ'אט: FastAPI שומר ב-Postgres ומפרסם ל-Redis, chat-ws ב-Go מנוי ודוחף ללקוח. בחרתי Go כי אלפי חיבורים idle זולים שם ולא שולפים load על SQLAlchemy."* |
| **הפניה** | [adr/ARCHITECTURE_DECISIONS_CHAT_WS.md](adr/ARCHITECTURE_DECISIONS_CHAT_WS.md) (כולל §7), HIGHLIGHTS §4 + Latest updates, [architecture/REALTIME.md](architecture/REALTIME.md), [chat-ws/README.md](../chat-ws/README.md) |

---

<a id="chat-thread-reconnect"></a>

## Chat thread — REST backfill על `WS onOpen` (`after`)

| | |
|--|--|
| **בעיה** | אם **`lastMessageIdRef`** היה **`null`** (שיחה בלי עדיין הודעות ב־state, או באג **`maxId \|\| null`**), הקוד הקודם **לא קרא** **`fetchMissedMessages`** בעליית החיבור — פער בשיחות בזמן ניתוק. בשלב מאוחר יותר: גם קריאה **בודדת** עם **`after`** ו־**`limit` 30** השאירה **זנב** שקט בהפסקות ארוכות (יותר מ־30 הודעות בפער). |
| **החלטה** | **`onopen` תמיד** — **`fetchMissedMessages(lastMessageIdRef ?? 0)`**; עדכון ref — **`messages.length > 0 ? max(message_id) : null`**. ההשלמה בפועל עוברת דרך **`fetchMissedGap`** — עמוד ראשון עם **`after`**, המשך עם **`before=next_cursor`** כל עוד **`has_more`**, בהתאם לחוזה ב־[API messages](architecture/API.md) (זהה ל־pagination של גלילה לעבר הישן). |
| **Trade-off** | הרבה יותר HTTP בפערים גדולים (עד **~50** עמודים × **`limit` 30**, עם **שני** ניסיונות חוזרים לכל עמוד); כפילויות נסגרות ע"י **`message_id`** ב־merge; אם הגענו למכסה או השיחה מתחלפת באמצע — חלק מהפער עלול להישאר (**`shouldAbort`** / **`cidRef`**). |
| **הפניה** | [architecture/REALTIME.md](architecture/REALTIME.md), [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md) (Latest updates), [`fetchMissedGap.ts`](../frontend/src/pages/MessageThread/fetchMissedGap.ts), [`fetchMissedGap.test.ts`](../frontend/src/pages/MessageThread/fetchMissedGap.test.ts), [`useChatWebSocket.ts`](../frontend/src/pages/MessageThread/useChatWebSocket.ts), [`useConversationMessages.ts`](../frontend/src/pages/MessageThread/useConversationMessages.ts) |

---

<a id="chat-optimistic-outbound"></a>

## Chat — optimistic outbound UI (frontend)

| | |
|--|--|
| **בעיה** | משתמש לוחץ Send ומחכה ל-REST — תחושת המתנה גם כשהרשת איטית; צריך גם ליישר עם WS שיכול להגיע לפני או אחרי תשובת השרת בלי כפילויות בבועות. |
| **החלטה** | רשימת הודעות ב-UI היא **`ChatListRow[]`**: **`confirmed`** (עוטף **`MessageResponse`**) או **`pending`** עם **`client_message_id`** (UUID). בשליחה: append **pending**, ניקוי שדה הקלט; ב-success REST או פריים WS — **`applyInboundRealMessage`** מסיר את ה-pending המתואם ומזין **`appendMessageDedupById`**; בכשל REST — **`removePendingByClientId`** והחזרת טקסט. **`useMessageThread`**: **`outboundPendingRef`** + **`processChatWebSocketMessage`**; **`useChatPopup`**: אותו מיזוג ללא WS. מפתח אידמפוטנטיות: **`consumeOrCreateKey` / `resetOutboundKey`** ללא שינוי. |
| **Trade-off** | שליחה בודדת בכל רגע (`sending`) — לא תור multi-flight; מודל pending לא נשמר ב-API (רק ב-state). |
| **הפניה** | [`types/chatList.ts`](../frontend/src/types/chatList.ts), [`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts), [`useMessageThread.ts`](../frontend/src/pages/MessageThread/useMessageThread.ts), [`useChatPopup.ts`](../frontend/src/components/ChatPopup/useChatPopup.ts), **ADR Frontend §2**, [ENGINEERING_HIGHLIGHTS.md](ENGINEERING_HIGHLIGHTS.md) (Latest updates) |

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
| **יתרון** | הגבלה הוגנת ברמת משתמש אותנטי, אטומיות מלאה ב-Lua, ללא שינוי בדומיין הצ'אט. |
| **Trade-off** | Redis למטה => fail-open לצורך זמינות (הגנה זמנית נחלשת). |
| **Interview pitch (≈30s)** | *"הוספתי rate limit פר-משתמש לשליחת הודעות בצ'אט, 30 לדקה, באלגוריתם Token Bucket אטומי דרך Lua script. fail-open אם Redis נופל כדי לא לשבור את הצ'אט."* |
| **הפניה** | [../backend/app/api/dependencies/rate_limit.py](../backend/app/api/dependencies/rate_limit.py), [../backend/app/domain/chat/router.py](../backend/app/domain/chat/router.py), [../ARCHITECTURE.md](../ARCHITECTURE.md), [#rate-limit-token-bucket](#rate-limit-token-bucket) |

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

## Frontend data layer — TanStack React Query

| | |
|--|--|
| **בעיה** | קריאות רשת מפוזרות יוצרות policy לא עקבי ל-retry/cache ושגיאות כפולות ב-Sentry בין axios interceptors לבין שכבות UI. |
| **החלטה** | `QueryClient` מרכזי עם `QueryCache`/`MutationCache`, retry policy מוגדר (network/5xx בלבד), תמיכה ב-`Retry-After` (seconds/date), ו-`mutations.retry=false`. |
| **Dedup שגיאות** | axios מסמן `__sentryCaptured` לפני capture ל-5xx; React Query `onError` בודק marker ולא מדווח שוב. `ERR_CANCELED` מדולג בשתי השכבות. |
| **Query key convention** | factories typed (`qk`/`mk`) במקום keys ידניים מפוזרים, כולל `Record<string, unknown>` לפילטרים. |
| **יתרון** | cache/retry עקביים בכל הדומיינים, observability נקייה יותר (בלי double-capture), ובסיס טוב למיגרציה הדרגתית של מסכים ל-RQ hooks. |
| **Trade-off** | שכבת תשתית נוספת בפרונט ודורשת משמעת של key factories כדי למנוע drift. |
| **הפניה** | [`../frontend/src/api/queryClient.ts`](../frontend/src/api/queryClient.ts), [`../frontend/src/api/queryKeys.ts`](../frontend/src/api/queryKeys.ts), [`../frontend/src/api/client.ts`](../frontend/src/api/client.ts), ADR Frontend §13 |

---

## React Query migration Stage 3b — Groups + MyRides

| | |
|--|--|
| **בעיה** | `GroupContext` ו-`MyRides` ניהלו fetch/state ידני (`useState` + `useEffect`), כולל עדכוני WS ב-`setState`, מה שהקשה על עקביות cache ועל תחזוקה. |
| **החלטה** | להעביר `GroupContext` ל-`useQuery(qk.groups.list)` ולשמור את `useGroup()` contract זהה; להעביר `MyRides` ל-`useQuery(qk.rides.list)` + `useMutation(mk.rides.cancel)` עם invalidate על אירועי WS. |
| **מדיניות cache** | `GroupContext` משתמש ב-`staleTime=2m`; `MyRides` ב-`staleTime=30s`; `refreshGroups` ממומש דרך `queryClient.invalidateQueries`. |
| **עדכון בזמן אמת** | אירועי `RIDE_FINISHED/RIDE_CANCELLED/RIDE_ENDED/RIDE_STARTED` גורמים ל-invalidate של `qk.rides.list` במקום patch ידני מרובה. |
| **יתרון** | מקור אמת יחיד לרשימות קבוצות/נסיעות, פחות race conditions בצד לקוח, ומיגרציה בטוחה בלי שינוי UX או מבנה JSX/CSS. |
| **Trade-off** | דורש משמעת גבוהה לשימוש עקבי ב-query keys ומדיניות invalidation כדי למנוע stale data. |
| **הפניה** | [`../frontend/src/context/GroupContext.tsx`](../frontend/src/context/GroupContext.tsx), [`../frontend/src/pages/MyRides.tsx`](../frontend/src/pages/MyRides.tsx), [`../frontend/src/api/queryKeys.ts`](../frontend/src/api/queryKeys.ts) |

---

## OpenAPI snapshot code generation (Orval)

| | |
|--|--|
| **בעיה** | טייפים/clients ידניים בפרונט נוטים לסטייה מה-schema של backend עם הזמן. |
| **החלטה** | לייצר client/types אוטומטית מ-`frontend/openapi-snapshot.json` באמצעות Orval (`orval.config.ts`) ל-`frontend/src/api/generated`, עם mutator אחיד (`apiMutator`) שמתחבר ל-axios instance הקיים. |
| **Source of truth** | קבצי generated נכנסים ל-git במכוון כדי לשמור reviewable API contract snapshot בכל commit. |
| **אכיפה ב-CI** | `frontend-ci` מריץ gate ייעודי: `npm run gen:api` ואז `git diff --exit-code -- src/api/generated/` (אחרי `git update-index -q --refresh`) כדי לחסום merge כשיש drift. |
| **יתרון** | מפחית drift חוזי בין backend/frontend, מקטין boilerplate ידני, ומשפר type-safety בזמן קומפילציה. |
| **Trade-off** | דורש discipline תהליכי: כל שינוי schema מחייב regeneration לפני merge. |
| **הפניה** | [`../frontend/orval.config.ts`](../frontend/orval.config.ts), [`../frontend/src/api/client.ts`](../frontend/src/api/client.ts), [`../frontend/src/api/generated/client.ts`](../frontend/src/api/generated/client.ts) |

---

## Auth forms — react-hook-form + zod

| | |
|--|--|
| **בעיה** | ניהול ידני/לא אחיד במסכי auth יוצר boilerplate וחזרתיות, ומגדיל סיכון לסטיות בין validation לבין submit state. |
| **החלטה** | לאחד את `Login`/`Register`/`VerifyEmail` תחת `react-hook-form` + `zodResolver`, עם סכמות ייעודיות לכל מסך ושמירת JSX/CSS ו-auth/navigation flow ללא שינוי. |
| **שימור behavior** | `Login` שומר `defaultValues` מ-`state?.email`; `Register` מחבר `PhoneInput` דרך `Controller`; `VerifyEmail` משאיר `resendLoading` נפרד ו-`formState.isSubmitting` ל-verify בלבד; שגיאות API נשארות ב-`error` state נפרד. |
| **יתרון** | קוד עקבי יותר בין כל מסכי auth, הפרדת אחריות נקייה (validation מול API errors), ותחזוקה פשוטה יותר להרחבות עתידיות. |
| **Trade-off** | תלות נוספת בפרונט ודורש משמעת סכמות/טיפוסים כדי להימנע מ-drift בין schema לשדות UI. |
| **הפניה** | [`../frontend/src/pages/Login.tsx`](../frontend/src/pages/Login.tsx), [`../frontend/src/pages/Register.tsx`](../frontend/src/pages/Register.tsx), [`../frontend/src/pages/VerifyEmail.tsx`](../frontend/src/pages/VerifyEmail.tsx), [`../frontend/package.json`](../frontend/package.json) |

---

## AdminLookup on-demand fetch — `useMutation` (React Query)

| | |
|--|--|
| **בעיה** | `AdminLookup` עבד עם manual async/state (`idle/loading/ready/error`) למרות שמדובר ב-trigger יזום משתמש (lookup לפי מזהה בלחיצה), מה שיצר state-machine אד-הוק מחוץ ל-RQ conventions. |
| **החלטה** | להעביר את flow ל-`useMutation` נפרד ל-ride ול-booking lookup, עם state נגזר מ-`isPending/isError/data` במקום `Result` ידני. |
| **שימור behavior** | UI נשאר זהה: אותם placeholders, כפתורים, הודעות `idle/loading/error`, ו-JSON output. ללא שינוי CSS. |
| **למה** | זה pattern נכון ל-imperative on-demand fetch ב-TanStack Query, מפחית state ידני, ומשפר עקביות ארכיטקטונית במסכי admin. |
| **Trade-off** | נוסף coupling קטן ל-RQ mutation state במסך יחיד, אבל הפחתת ה-boilerplate והסיכון ל-state drift עדיפה. |
| **הפניה** | [`../frontend/src/features/admin/pages/AdminLookup.tsx`](../frontend/src/features/admin/pages/AdminLookup.tsx), [`../frontend/src/features/admin/api/lookup.ts`](../frontend/src/features/admin/api/lookup.ts) |

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

<a id="slos-error-budgets"></a>

## SLOs & Error Budgets

| | |
|--|--|
| **בעיה** | dashboards ולוגים נותנים observability, אבל בלי יעדי שירות רשמיים קשה להחליט מתי המערכת “מספיק יציבה” ומתי לעצור rollout בגלל אמינות. |
| **החלטה** | להגדיר SLO framework מעל metrics הקיימים: backend latency/availability + worker reliability counters (RabbitMQ/Outbox/AI/Billing). המדיניות מתורגמת ל-error budget חודשי שמנווט החלטות delivery. |
| **אלטרנטיבות** | (1) לפעול לפי alerts בלבד. (2) להסתמך על “health=ok” בלי SLA/SLO. (3) SRE פורמלי כבד מדי מוקדם מדי. |
| **יתרון** | יישור בין product למהנדסים: ברור מתי ממשיכים לפיצ'רים ומתי משקיעים באמינות; התראות הופכות לפעולה מדידה ולא “תחושת בטן”. |
| **Trade-off** | דורש תחזוקה של dashboards/alerts ושיפור מתמיד של SLI definitions כדי להימנע מ-targets לא ריאליים. |
| **Interview pitch (≈30s)** | *"אחרי שהטמענו metrics בבקאנד ובעובדים, הוספנו שכבת SLOs: availability + p95/p99 + async success ratio עם error budget חודשי. זה נותן governance לפרודקשן — לא רק לראות גרפים אלא גם להחליט מתי לעצור rollout ולתקן אמינות."* |
| **הפניה** | [`../backend/app/infrastructure/metrics.py`](../backend/app/infrastructure/metrics.py), [`../backend/app/workers/notification_worker.py`](../backend/app/workers/notification_worker.py), [`../backend/app/workers/task_worker.py`](../backend/app/workers/task_worker.py), [`../backend/app/workers/ai_worker.py`](../backend/app/workers/ai_worker.py), [`../monitoring/prometheus.yml`](../monitoring/prometheus.yml) |

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

<a id="chat-message-idempotency"></a>

## Idempotency-Key — `POST …/chat/conversations/{id}/messages`

| | |
|--|--|
| **בעיה** | double tap / retry רשת → שתי הודעות DB לאותה כוונה בשיחה. |
| **החלטה** | כותרת אופציונלית, מפתח Redis נפרד (`idempotency:chat_message:{user_id}:{key}`), fingerprint על `conversation_id` + תוכן; cache רק **201**; 409/`Retry-After` בזמן processing; **fail-open** בלי Redis — אותם עקרונות כמו §19. |
| **אלטרנטיבות** | (1) idempotency רק ב-UI — לא אמין. (2) unique digest ב-DB — דורש schema + edge cases למחיקות. |
| **יתרון** | אותו story כמו Stripe/e-commerce; `message_idempotency.py` + router דק בלי להזיז לוגיקת שמירה עמוקות. |
| **Trade-off** | בלי Redis אין dedup. |
| **Interview pitch (≈30s)** | *“החלפתי את אותה מסגרת Stripe-style מנסיעות לצ’אט: מפתח פר-משתמש, fingerprint על conversation+body, שומרים רק תשובת הצלחה.”* |
| **הפניה** | ADR §25, Frontend ADR §2, HIGHLIGHTS (Latest updates + §7ה); [Chat — optimistic outbound UI](#chat-optimistic-outbound); [`frontend/src/api/chat.ts`](../frontend/src/api/chat.ts), [`types/chatList.ts`](../frontend/src/types/chatList.ts), [`useMessageThread.ts`](../frontend/src/pages/MessageThread/useMessageThread.ts), [`useChatPopup.ts`](../frontend/src/components/ChatPopup/useChatPopup.ts), [`chatMessagesMerge.ts`](../frontend/src/utils/chatMessagesMerge.ts) |

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

## Circuit Breaker — Google Maps + Brevo email (באקאנד)

| | |
|--|--|
| **בעיה** | Geocoding/Directions איטי או 429 → storm של requests; Brevo down + Tenacity על ה-SDK → retries מציפים את הספק ואת ה-worker. |
| **החלטה** | מחלקה משותפת **`CircuitBreaker`** עם `Gauge` מוזרק; **גיאו:** מעגל in-memory לכל API — OPEN = אין HTTP ל-Google; **מייל:** `brevo_email_cb` — OPEN = `EmailProviderCircuitOpenError` בלי קריאה ל-Brevo (Tenacity רק כשהמעגל מאפשר). health מדווח `circuit_breakers` (כולל `brevo_email`) בלי לסמן את השרת unhealthy. |
| **אלטרנטיבות** | (1) Retry בלי cap — מחמיר. (2) rate limit בלבד. (3) sidecar (Envoy) — overkill. |
| **יתרון** | fail-fast; מגן על CPU ו-external budget; מדדי `geo_*` / `brevo_*` נפרדים. |
| **Trade-off** | מעגל **לא** משותף בין instances — reset אחרי deploy. |
| **Interview pitch (≈30s)** | *"מחלקה אחת, שני סוגי מדדים: גיאו — מעגל לכל API; Brevo — מעגל לפני ה-SDK. Health מציג מצב אבל status הכללי תלוי DB/Redis/Rabbit בלבד."* |
| **הפניה** | ADR §20, HIGHLIGHTS §0א, `docs/architecture/NOTIFICATIONS.md` |

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

[← חזרה ל-Interview Playbook](internal/INTERVIEW_PLAYBOOK.md)

---

<a id="pgbouncer"></a>

## PgBouncer (EC2 + Docker Compose)

| | |
|--|--|
| **בעיה** | כמה services (backend + workers) עם pools נפרדים יוצרים fan-out לחיבורי Postgres תחת עומס/redeploy. ב-EC2 בינוני זה פוגע בזיכרון/latency לפני CPU saturation. |
| **החלטה** | להוסיף `pgbouncer` כ-service פנימי ב-Compose (transaction mode), ולהעביר runtime services ל-`POSTGRES_HOST=pgbouncer`. |
| **אלטרנטיבות** | (1) להגדיל רק `max_connections` ב-Postgres — מטפל סימפטום ולא שורש. (2) בלי pooler, רק להקטין `DB_POOL_*` — עוזר חלקית. (3) RDS Proxy/managed pooler — עדיף בענן מנוהל אבל לא quickest win ב-EC2 קיים. |
| **מה סניור עושה (לא טריוויאלי)** | (1) `migrate` נשאר direct ל-`db` ולא דרך pooler. (2) asyncpg statement cache מנוטרל (`statement_cache_size=0`) לתאימות transaction pooling. (3) PgBouncer internal-only בלי פתיחת `6432` לציבור. (4) right-size ל-SQLAlchemy pools כדי להימנע מ-double-pooling אגרסיבי. (5) אם images ציבוריים דורסים config דרך entrypoint — עוברים ל-custom image מבוקר במקום workaround שביר. (6) `userlist.txt` אמיתי לא נכנס ל-git: יוצרים בזמן deploy מ-template עם `envsubst` ו-`chmod 600`. |
| **יתרון** | connection storms נבלמים מוקדם, יותר יציבות בזמן deploys, ו-headroom להמשך scaling בלי שינוי לוגיקה דומיינית. |
| **Trade-off** | עוד רכיב תפעולי לנטר (health/config/auth), וצריך משמעת סביב סודות `userlist` + smoke checks בפריסה. |
| **Interview pitch (≈30s)** | *"במקום שכל service יפציץ את Postgres בחיבורים, הוספתי PgBouncer כ-layer פנימי. השארתי migrations direct ל-db, כיביתי statement cache ב-asyncpg, והקטנתי pools אפליקטיביים — זה בדיוק ההבדל בין 'להוסיף container' לבין rollout יציב ברמת production."* |
| **הפניה** | `docker-compose.yml`, `backend/app/db/session.py`, `infrastructure/pgbouncer/{Dockerfile,pgbouncer.ini,userlist.txt.template}`, `.github/workflows/backend-ci.yml`, `scripts/ops/pgbouncer-smoke.sh` |

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

---

<a id="rabbitmq-self-healing"></a>

## RabbitMQ self-healing consumer loop

| | |
|--|--|
| **בעיה** | אחרי ניתוק/סגירת channel, iterator של `aio_pika` יכול להיסגר ו-consumer להפסיק לעבוד עד restart חיצוני. |
| **החלטה** | `consume()` הפך ללולאת self-healing: recreate iterator/channel, bounded backoff על `_setup()` failures, draining מסודר, ומדד אופרטיבי `rabbitmq_consumer_iterator_restarts_total`. |
| **אלטרנטיבות** | (1) להסתמך רק על supervisor restart. (2) ליצור consumer חדש בכל restart חיצוני בלי recovery פנימי. |
| **יתרון** | עמידות טובה יותר לבעיות Rabbit transient בלי dependency על restart orchestration. |
| **Trade-off** | מורכבות לולאת consume עולה ודורשת observability כדי להבחין בין transient noise לבין תקלה כרונית. |
| **Interview pitch (≈30s)** | *"במקום שריסטארט תהליך יהיה הפתרון, ה-consumer מרפא את עצמו: אם iterator נסגר הוא נבנה מחדש עם backoff ומדד iterator restarts. כך מפחיתים downtime שקט של תורים."* |
| **הפניה** | `backend/app/infrastructure/rabbitmq/consumer.py`, `backend/app/infrastructure/metrics.py` |

---

<a id="frontend-runtime-config"></a>

## Frontend runtime config (12-factor)

| | |
|--|--|
| **בעיה** | `import.meta.env` ב-Vite מחליף ערכים בזמן build; image שנבנה בלי `VITE_*` גורם לפרונט שבור (`projectId` חסר ב-Firebase). |
| **החלטה** | לעבור ל-runtime config: entrypoint מייצר `config.js` + `firebase-messaging-sw.js` עם `envsubst`; הקוד קורא `window.__APP_CONFIG__` עם fallback ל-`import.meta.env` בדב. |
| **אלטרנטיבות** | (1) build-args + GH Secrets לכל VITE. (2) hardcode ציבורי בקוד. |
| **יתרון** | image agnostic לסביבה; שינוי קונפיג = restart, לא rebuild/pipeline. |
| **Trade-off** | עוד שכבת bootstrap בפרונט (template + entrypoint) וחובה לנהל env files בשרת בצורה עקבית. |
| **Interview pitch (≈30s)** | *"הוצאתי קונפיג פרונט מזמן build לזמן runtime. אותו image רץ בכל סביבה, וה-entrypoint מייצר config.js מה-env. זה 12-factor נקי ומונע drift בין builds."* |
| **הפניה** | `frontend/docker/40-render-config.sh`, `frontend/src/config/runtime.ts`, `docker-compose.yml` |

---

<a id="deploy-env-sot"></a>

## Deploy env single source-of-truth (multi env-file + JWT sync)

| | |
|--|--|
| **בעיה** | Compose interpolates env from selected env-file בלבד; בלי `frontend/.env` ערכי `VITE_*` לא נטענים, ובלי סנכרון סודות אפשר mismatch בין backend/chat-ws. |
| **החלטה** | deploy script משתמש ב-`--env-file backend/.env --env-file frontend/.env`, מוסיף fail-fast guards לקבצים חסרים, ומסנכרן `JWT_SECRET` ב-`chat-ws/.env` מתוך `backend SECRET_KEY`. |
| **אלטרנטיבות** | (1) root `.env` ענק לכל השירותים. (2) GH Secrets ל-VITE ציבוריים. (3) סנכרון ידני של JWT בין קבצים. |
| **יתרון** | source-of-truth ברור לכל שכבה + הפחתת config drift בפריסות. |
| **Trade-off** | יש תלות במשמעת ops סביב `.env.production` לכל שירות ו-copy step תקין לפני compose up. |
| **Interview pitch (≈30s)** | *"חילקנו env לפי גבולות שירות אבל פריסה מרכיבה אותם במפורש. זה שומר runtime deterministic וגם מונע JWT mismatch בין backend ל-chat-ws."* |
| **הפניה** | `.github/workflows/backend-ci.yml`, `docker-compose.yml` |

---

<a id="oauth-popup-coop"></a>

## OAuth popup compatibility (COOP/COEP headers)

| | |
|--|--|
| **בעיה** | Google OAuth popup עלול להיחסם ל-`window.postMessage` בגלל מדיניות COOP קשיחה. |
| **החלטה** | הוספת headers ב-nginx: `Cross-Origin-Opener-Policy: same-origin-allow-popups` ו-`Cross-Origin-Embedder-Policy: unsafe-none` (עם `always`). |
| **אלטרנטיבות** | (1) לנסות flow בלי popup. (2) להחליש headers חלקית ברמת נתיב בלי ניתוח מלא של השפעה. |
| **יתרון** | תיקון יציב ל-flow OAuth הקיים בלי לשנות לוגיקת auth בפרונט/בקאנד. |
| **Trade-off** | מדיניות COOP/COEP פחות קשיחה לטובת תאימות OAuth popup. |
| **Interview pitch (≈30s)** | *"שגיאת popup postMessage נפתרה בשכבת ה-edge, לא ב-workaround בפרונט. הוספנו COOP/COEP תואם ל-Google popup תוך שמירה על HTTPS flow מלא."* |
| **הפניה** | `nginx/nginx.conf` |

---

<a id="single-ec2-cd"></a>

## Single-EC2 CD rolling deploy (no ALB)

| | |
|--|--|
| **בעיה** | Deploy ידני ב-SSH יוצר אי-עקביות וסיכון לטעות אנוש; Blue/Green מלא מכפיל משאבים ויקר מדי ל-`t3.medium`. |
| **החלטה** | ליישם CD פרגמטי ב-GitHub Actions: build+push (`latest` + `sha`) ואז deploy ל-EC2 ב-SSH, rollout ל-backend יחיד עם `docker compose up -d --no-deps backend`, health gate, ו-rollback אוטומטי לתג קודם. |
| **אלטרנטיבות** | (1) ALB + target groups + שני סטאקים — הכי נקי תיאורטית אבל תוספת עלות/מורכבות. (2) Blue/Green מקומי עם שני compose projects — כמעט פי 2 footprint בזמן rollout. (3) להישאר manual deploy — פשוט אך לא אמין לאורך זמן. |
| **מה סניור עושה (לא טריוויאלי)** | (1) משתמש ב-immutable `sha` ל-deterministic rollback. (2) שומר `previous tag` בצד השרת ולא מסתמך על `latest`. (3) deploy נחשב נכשל אם health לא עולה בזמן מוגדר. (4) מוסיף `stop_grace_period` ו-tuning בסיסי ב-nginx כדי לצמצם impact בזמן החלפה. |
| **יתרון** | תהליך פריסה אוטומטי, עקבי ומהיר, שמתאים לתקציב קטן ולשרת יחיד בלי לבנות פלטפורמה כבדה. |
| **Trade-off** | זה low-downtime ולא zero-downtime מוחלט, כי backend רץ כרגע בעותק יחיד בזמן ההחלפה. |
| **Interview pitch (≈30s)** | *"בחרתי CD פרגמטי לשרת יחיד: SHA-tag deploy + health gate + auto rollback. זה נותן אמינות תפעולית גבוהה בלי לשלם על ALB/תשתית כפולה, ומתאים לשלב הסקייל הנוכחי."* |
| **הפניה** | `.github/workflows/backend-ci.yml`, `docker-compose.yml`, `nginx/nginx.conf`, `docs/architecture/DEVELOPMENT.md` |

---

<a id="rate-limit-token-bucket"></a>

## Rate limiting — Token Bucket + Sliding Window (atomic Lua)

| | |
|--|--|
| **בעיה** | המימוש הקודם השתמש ב-`INCR + EXPIRE` בשתי פקודות נפרדות. בגבול חלון אפשר היה לשלוח **פי 2** מהמותר: לדחוף `max_count` בקצה החלון, ה-counter מתאפס באלפית שנייה לאחר מכן, ולשלוח `max_count` נוספים מיד. בנוסף, אותו אלגוריתם שירת גם auth (anti-bruteforce) וגם chat (API throttle) — שתי דרישות סותרות. |
| **החלטה** | להחליף ב-**שני** Lua scripts אטומיים שונים, מותאמים לאיום: <ul><li>**Auth** (`rate_limit_auth`) → **Sliding-Window Log** (`sliding_window.lua`, sorted-set פר IP). אין burst, חלון מתגלגל אמיתי. תוקף ששתק 10 דקות לא מקבל "קופונים" — כל ניסיון נכנס לחלון הנוכחי בלבד.</li><li>**Chat** (`rate_limit_chat`) → **Token Bucket** (`token_bucket.lua`, hash פר משתמש). Burst עד `capacity` מותר ואף רצוי ל-API; refill חלק (`refill_per_sec`).</li></ul> שני ה-scripts רצים אטומית בתוך Redis, נטענים פעם אחת דרך `register_script` של redis-py (שמטפל אוטומטית ב-`EVALSHA` ו-fallback ל-`EVAL` על `NOSCRIPT` אחרי Sentinel failover או `SCRIPT FLUSH`). |
| **API ל-clients** | החריג `RateLimitExceeded` מועשר ל-`{retry_after, limit, remaining}`, וה-handler המרכזי פולט 4 כותרות סטנדרטיות (Stripe / GitHub convention): `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (epoch seconds), `Retry-After`. בלי זה, ה-client לא יודע מתי לנסות שוב → retry loop אגרסיבי → DDoS עצמי. |
| **אלטרנטיבות שנפסלו** | (1) Token Bucket אחד לשניהם — נחלש מול attacker שמקבץ "קופונים" בעת שקט ואז יורה ב-burst. (2) Leaky bucket — overkill לתרחיש שלנו. (3) `redis.call('TIME')` במקום זמן מהקליינט — דורש `replicate_commands()` ו-non-determinism; זמן מ-EC2 (chrony NTP) מספיק מדויק. (4) wrapper לאחור על `rate_limit_check` — leaky abstraction; עדיף למחוק (יש רק 2 call sites בפרויקט). |
| **Fail-open** | כל `RedisError` או `register_script` שנכשל → `RateLimitResult.fail_open` → הבקשה עוברת. הגנה היא defense-in-depth, ולא כדאי שתפיל login/chat בזמן outage של Redis. נמדד ב-`rate_limit_redis_errors_total{endpoint}`. |
| **Trade-offs (מודעים)** | (1) זמן wall clock מועבר מהקליינט ל-Lua → drift אפשרי בקנה מידה NTP (≪10ms ב-EC2 עם chrony) — מקובל ל-rate limiting. (2) Lua 5.1 לא מבחין int/float; precision של refill תקין לסקאלות שעון אנושיות (שניות-דקות). (3) Sliding-window log שומר entry per request → memory `O(max_count)` לכל מפתח — סביר לעשרות בקשות בחלון. |
| **מטריקות** | `rate_limit_rejected_total{algorithm,endpoint}`, `rate_limit_redis_errors_total{endpoint}`, `rate_limit_evaluation_seconds{algorithm}` (Histogram). |
| **Interview pitch (≈45s)** | *"זיהיתי ש-`INCR+EXPIRE` בשתי פקודות מאפשר 2x burst בגבול החלון. ההחלטה הסניורית הייתה לא רק לתקן עם Lua, אלא להפריד לשני אלגוריתמים: sliding window log ל-auth כי שם burst הוא בדיוק הבעיה (anti-bruteforce), ו-token bucket ל-chat כי שם burst רצוי. שני scripts אטומיים, נטענים פעם אחת דרך register_script של redis-py שמטפל ב-EVALSHA וב-NOSCRIPT אחרי Sentinel failover. ההחזרה היא typed result עם limit/remaining/retry_after_ms שמתורגם ל-X-RateLimit-* headers — זה מה ש-Stripe ו-GitHub עושים, וזה מונע retry storms של clients."* |
| **הפניה** | [`../backend/app/infrastructure/redis/lua/token_bucket.lua`](../backend/app/infrastructure/redis/lua/token_bucket.lua) · [`../backend/app/infrastructure/redis/lua/sliding_window.lua`](../backend/app/infrastructure/redis/lua/sliding_window.lua) · [`../backend/app/infrastructure/rate_limiter.py`](../backend/app/infrastructure/rate_limiter.py) · [`../backend/app/api/dependencies/rate_limit.py`](../backend/app/api/dependencies/rate_limit.py) · [`../backend/app/core/exceptions/handlers.py`](../backend/app/core/exceptions/handlers.py) · ADR §23 |

---

<a id="audit-log-admin-billing"></a>

## Audit log (admin + billing webhook attempts)

| | |
|--|--|
| **בעיה** | לוגים טקסטואליים בלבד (`[admin_audit]`) לא מספיקים לחקירה אמינה לאורך זמן; בנוסף, ב-billing יש event idempotency (`stripe_event_id`) שמסנן retries ולכן בלי סדר נכון מאבדים תיעוד של ניסיונות כפולים. |
| **החלטה** | טבלת `audit_log` ייעודית (append-only) + repository (`audit_repo.record`). פעולות אדמין רגישות כותבות גם ל-DB וגם ל-logger. ב-`checkout.session.completed` audit attempt נכתב **לפני** בדיקת idempotency כדי לתעד גם duplicate webhook deliveries. |
| **אלטרנטיבות** | (1) להישאר רק עם structured logs. (2) לשלוח audit ל-SIEM חיצוני בלבד. (3) Outbox ייעודי לכל audit event (מורכב יותר כרגע). |
| **יתרון** | forensic trail יציב עם סינון לפי actor/resource/action וזמן; מונע blind spot בסנריו של retries מ-Stripe. |
| **Trade-off** | עוד טבלת write-path בפרודקשן ונפח metadata שדורש משמעת; לכן metadata נשמר קומפקטי ולא payload מלא. |
| **Interview pitch (≈30s)** | *"הוספתי audit persistence לדברים הרגישים באמת, וב-billing הקפדתי לכתוב audit לפני idempotency כדי שגם retries כפולים יהיו traceable. זה ההבדל בין log נוח לבין evidence אמין לחקירה."* |
| **הפניה** | `backend/app/domain/admin/router.py`, `backend/app/domain/billing/service.py`, `backend/app/infrastructure/audit/{model.py,repo.py}`, `backend/alembic/versions/015_add_audit_log.py`, ADR §24 |
