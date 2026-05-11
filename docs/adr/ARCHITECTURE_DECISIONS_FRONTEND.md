# החלטות ארכיטקטוניות — Frontend (Web)

מסמך להצגה בראיון: **למה** אפליקציית הווב בנויה כפי שהיא. פירוט מבנה תיקיות וזרימות: [../../frontend/docs/ARCHITECTURE.md](../../frontend/docs/ARCHITECTURE.md).

---

## 1. React + Vite + TypeScript

| | |
|--|--|
| **הקשר** | SPA שמדברת ל-API נפרד (FastAPI) ול-chat-ws; UI בעברית RTL. |
| **החלטה** | **React 19**, **TypeScript**, **Vite** ככלי build ו-dev server. |
| **למה** | DX טוב, build מהיר, אקוסיסטם גדול; TypeScript כחוזה בין UI לשכבת API. |
| **אלטרנטיבה** | Next.js — פחות נחוץ כשאין SSR כמטרה ראשית וה-API כבר מנותק; נשארנו ב-SPA פשוטה מאחורי proxy ב-Vite. |
| **בקצרה לראיון** | "SPA עם Vite — מהירות פיתוח ובילד, וה-API נשאר שירות עצמאי." |

---

## 2. שכבת API מול `client`

| | |
|--|--|
| **החלטה** | עטיפות דקות ב-`src/api/*.ts` סביב ה-`Axios` ב-[`client.ts`](../../frontend/src/api/client.ts); **לא** לייבא `api` ישירות מקומפוננטות מלבד חריגים מבוקרים. |
| **חריגים** | `AuthContext` (טוקנים, interceptors), ו-[`api/presence.ts`](../../frontend/src/api/presence.ts) (`chatWsApi`) — מתועדים ב-ARCHITECTURE של הפרונט. |
| **למה** | קל לחפש endpoints, לאחד headers ו-refresh, ולשמור על גבול ברור בין UI לרשת. |
| **בקצרה לראיון** | "מרכזים HTTP ב-client אחד; הדומיין קורא פונקציות מ-api ולא נתיבים גולמיים." |
| **Idempotency (צ’אט outbound)** | **`POST …/messages`**: אותו דפוס מחזור חיים כמו **`useJoinRide`** — **`consumeOrCreateKey`** / **`resetOutboundKey`** ([`outboundIdempotencyKey.ts`](../../frontend/src/utils/outboundIdempotencyKey.ts)) ב־**`useMessageThread`** ו-**`useChatPopup`**; מפתח מפורש ל־[**`sendMessage`**](../../frontend/src/api/chat.ts). **רשימת הודעות:** union **`ChatListRow`** ([`types/chatList.ts`](../../frontend/src/types/chatList.ts)) — **`confirmed`** / **`pending`** (`client_message_id`); **`applyInboundRealMessage`** קורא ל־**`appendMessageDedupById`** ([`chatMessagesMerge.ts`](../../frontend/src/utils/chatMessagesMerge.ts)) אחרי הסרת pending מתואם; אותו מיזוג מ־[**`processChatWebSocketMessage`**](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.ts) עם **`outboundPendingRef`** (thread בלבד) כדי ליישר WS לפני/אחרי REST בלי כפילויות. כשל REST: **`removePendingByClientId`** והחזרת טקסט. **422 mismatch:** **`isChatIdempotencyKeyMismatch`** ב־[`apiError.ts`](../../frontend/src/utils/apiError.ts). |

---

## 3. RTL ועברית

| | |
|--|--|
| **החלטה** | ממשק בעברית; כיוון RTL (למשל כרטיסי מסלול origin ← destination); עקביות עם המוצר המקומי. |
| **למה** | UX טבעי למשתמשי יעד; CSS Modules וטוקנים גלובליים (`tokens.css`) תומכים בעקביות ויזואלית. |
| **בקצרה לראיון** | "המוצר נבנה RTL-first — זה משפיע על פריסה, אייקונים וטקסטים." |

---

## 4. Real-time בווב — שני שרתי WS + Zod

| | |
|--|--|
| **הקשר** | צ'אט, נסיעות, מיקום, התראות in-app, אירועי משתמש (`user:*:events`). |
| **החלטה** | **צ'אט** + אירועי **`user:{id}:events`** (כולל **`invalidate`** ל-unread והתראות + **`UserEvent`**) דרך **chat-ws** (Go); **נסיעות / מיקום** דרך **WebSocket של FastAPI** (ראו [WEBSOCKETS.md](WEBSOCKETS.md)). רשימת התראות — **REST** (`fetchMyNotifications`). פריימים נכנסים עוברים **Zod** (`safeParse`) ב-[`wsEvents.ts`](../../frontend/src/types/wsEvents.ts) ובעיבוד הודעות צ'אט ב-[`processChatWebSocketMessage.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.ts). |
| **למה Zod** | חוזה בזמן ריצה מול JSON מהרשת; פחות `as` לא בטוחים; בדיקות יחידה על סכמות. |
| **בקצרה לראיון** | "לא סומכים על צורת JSON מה-WS — מאמתים עם Zod לפני שמעדכנים state." |

---

## 5. פיד התראות in-app — REST + `user:{id}:events` על chat-ws + polling גיבוי

| | |
|--|--|
| **החלטה** | [`useChatNotificationsFeed`](../../frontend/src/context/useChatNotificationsFeed.ts) — React Query על **`GET /api/v1/users/me/notifications`** + **polling** כל **~5 דקות**. רענון חי: **`useUserEventStream`** ב-[`ChatContext.tsx`](../../frontend/src/context/ChatContext.tsx) (סדר פרסור: Invalidate → UserEvent); לתאימות מסכים — **`linkup:user-event`** בענף התראות. מסכים אחרים עדיין יכולים להשתמש ב־**`useUserEvent`** על ה-custom event. אין WS נפרד לפיד. |
| **למה** | מקור אמת לרשימה ב-REST; דחיפת UI על אותו WS כמו הצ'אט; polling דל כשהאירועים לא מגיעים. |
| **למה backoff (פרונט)** | לצ'אט ול-WS של FastAPI — **exponential backoff + jitter** ב-[`reconnectBackoff.ts`](../../frontend/src/utils/reconnectBackoff.ts) (`useChatWebSocket`, `useReconnectingWebSocketState`) כדי להפחית thundering herd אחרי נפילה המונית. |
| **בקצרה לראיון** | "רשימת התראות מ-REST עם polling דל; רענון חי דרך אירועי משתמש על chat-ws — בלי WS נוסף לפיד." |

---

## 6. FCM (Push)

| | |
|--|--|
| **החלטה** | data-only מהשרת; Toast + Service Worker בפרונט; `devLog` רק ב-DEV. |
| **לעומק** | [FCM_AND_PUSH.md](FCM_AND_PUSH.md), [../FCM_SYSTEM_SUMMARY.md](../FCM_SYSTEM_SUMMARY.md). |
| **בקצרה לראיון** | "שליטה אחידה על UX ב-foreground וב-background — לא משאירים את FCM להציג הודעות אוטומטיות בלי הקוד שלנו." |

---

## 7. מצב גלובלי ו-My Bookings

| | |
|--|--|
| **החלטה** | `AuthContext`, `ChatContext`, `GroupContext`; לוגיקת צ'אט/התראות מפוצלת ל-hooks קטנים (`useChatUnreadMessages`, וכו'). **הזמנות שלי**: קומפוזיציה ב-[`useMyBookings.ts`](../../frontend/src/pages/MyBookings/useMyBookings.ts) עם **מבנה החזרה מקונן** (`passenger`, `driver`, `chat`); יצוא **`MyBookingsViewModel`**. נתונים מ־**`/bookings/*-summary/active`** + **`/history`** (קורסור) — בלי N+1. |
| **למה** | גבולות אחריות ברורים; חוזה VM קריא; פחות רשת ורינדורים מיותרים. |
| **בקצרה לראיון** | "מפרידים hooks לפי דומיין; VM מקונן; שרת מאחד קריאות לטאב נהג/נוסע." |

---

## 8. אדמין

| | |
|--|--|
| **החלטה** | נתיבים תחת `/admin` **נטענים בעצלנות** (lazy); [`AdminRoute`](../../frontend/src/features/admin/components/AdminRoute.tsx) דורש משתמש + `is_admin` מ-JWT/context; UX **דסקטופ** (סיידבר) — ראו [../../ADMIN_DASHBOARD.md](../../ADMIN_DASHBOARD.md). |
| **למה** | פחות bundle למשתמש רגיל; אבטחה בשכבת UI בנוסף לבדיקת שרת. |
| **בקצרה לראיון** | "אדמין מבודד ב-lazy routes ומוגן ב-AdminRoute — העומס הראשי לא נטען לכל משתמש." |

---

## 9. טיפול בשגיאות

| | |
|--|--|
| **החלטה** | [`useErrorHandler`](../../frontend/src/errors/useErrorHandler.ts) מנרמל Axios ופורמט ה-API (`error_code`, `message`, `trace_id`); [`CODE_MESSAGES`](../../frontend/src/errors/useErrorHandler.ts) למיפוי קודים נפוצים לעברית כשאין הודעה מהשרת. |
| **למה** | התאמה ל-[`docs/ERRORS.md`](../ERRORS.md) — חוויית משתמש אחידה גם כשהשרת מחזיר רק קוד. |
| **בקצרה לראיון** | "מיישרים קו עם LinkUpError בבקאנד — קוד שגיאה, הודעה, ו-fallback לפי error_code." |

---

## 10. i18n (עברית + אנגלית)

| | |
|--|--|
| **החלטה** | **i18next** + `react-i18next`; משאבים תחת [`frontend/src/i18n/locales/`](../../frontend/src/i18n/locales/) (`he` / `en`), כולל מפתחות **`common:err_*`** לטקסטי שגיאה כלליים ו-**`rides:err_*`** לשגיאות ולידציה ספציפיות לדומיין (geolocation, מוצא/יעד, מסלול). UI copy בדפים (`Messages.tsx`) משתמש ב-**`common:msg_*`** / **`common:unread_count`** / **`common:user_fallback`**. |
| **למה** | מוצר מקומי עם אפשרות הדגמה/שימוש ב-LTR; מחרוזות UI ושגיאות נשארות מתורגמות גם מחוץ לרכיבי React (hooks) דרך `i18n.t`. |
| **בקצרה לראיון** | "אפס עברית קשיחה ב-hooks ובדפים — `common` ל-UI כללי, `rides:err_*` לולידציות דומיין, `apiErr` ל-fallback שגיאות שרת." |
| **עדכון S.7** | `common`/`nav` נשארים **bundled** ב-`src/i18n/config.ts`, בעוד namespaces פיצ'ריים (`auth`,`rides`,`bookings`,`groups`,`profile`,`billing`) נטענים עצלנית דרך `i18next-http-backend` מ-`/locales/{{lng}}/{{ns}}.json` (מקור אמת נשאר ב-`src/i18n/locales`, והעתקה runtime ב-`public/locales`). |
| **ניקוי מפתחות מתים** | סריקה אוטומטית של כל ~430 מפתחות מול קבצי מקור; הוסרו **57 מפתחות לא בשימוש** (~13%) מ-6 namespaces (`rides`, `bookings`, `groups`, `profile`, `auth`, `common`) — מפתחות שהוחלפו (`resendCode` → `resendNewCode`, `noBookingsPassenger` → `noPassengerBookings`, `driverTab` → `iAmDriver`), שגיאות ללא קריאה, ותוויות UI ישנות. `billing` ו-`nav` היו נקיים לחלוטין. תוקן באג runtime: `backend_timeout` ו-`error_origin_not_allowed` היו חסרים מ-`public/locales/auth.json` (הקובץ הנטען בפועל) למרות שקיימים ב-`src/i18n/locales/auth.json`. |

---

## 11. פורמט תאריכים ושעות לפי לוקאל

| | |
|--|--|
| **החלטה** | [`getLocale()`](../../frontend/src/utils/date.ts) נגזר מ־`i18n.language` (`he-IL` / `en-US`); פונקציות עזר (`formatTimeHm`, `formatWeekdayLong`, `formatMonthYearLong`, וכו') ל־`toLocaleString` / ICU במקום מחרוזות קשיחות. |
| **למה** | אותו קוד תומך בשתי השפות בלי לשכפל לוגיקת תצוגה. |
| **בקצרה לראיון** | "תאריכים עוקבים אחרי שפת הממשק, לא אחרי שפה קבועה בקוד." |

---

## 12. טיפוגרפיה ב-CSS Modules

| | |
|--|--|
| **החלטה** | ב־**`*.module.css`** — `font-family: var(--font-primary)` (ולמספרים: `var(--font-numeric)`); **`LangContext`** מגדיר `--font-primary` על הדף לפי שפה. **חריג:** [`LangToggle.module.css`](../../frontend/src/components/LangToggle/LangToggle.module.css) נשאר עם פונט מונוספי לווידג'ט. |
| **למה** | מקור אמת אחד לפונט גוף; מעבר שפה מעדכן טיפוגרפיה בלי לשכפל fallback של Heebo בכל קובץ. |
| **בקצרה לראיון** | "טוקן CSS אחד לפונט גוף — בדומה לצבעים ב־`tokens.css`." |

---

## 13. React Query infrastructure (QueryClient + keys + error ownership)

| | |
|--|--|
| **הקשר** | שכבת רשת עשירה עם retries, שגיאות transport, ומספר דומיינים עם reads/mutations חוזרות. נדרש סטנדרט אחיד לקאשינג, retry policy ו-observability בלי double-capture ב-Sentry. |
| **החלטה** | להוסיף `QueryClient` מרכזי ב־[`frontend/src/api/queryClient.ts`](../../frontend/src/api/queryClient.ts) עם `QueryCache`/`MutationCache`, wrapper `captureExceptionOnce`, ו-policy אחיד: `staleTime`, `gcTime`, retry רק לשגיאות retryable (network/5xx), `Retry-After` parsing (delta/date), ו-`mutations.retry=false`. |
| **Dedup pattern (Sentry)** | ה-axios interceptor מסמן `__sentryCaptured=true` לפני capture ל-**5xx**; אחרי **401** בסוף ניסיון refresh כושל הוא מסמן לפני `reject` (**defense-in-depth** בעד **`captureExceptionOnce`** מה-React Query). ב-React Query `onError`: **401** מתעלם (`shouldSkipSentryForApiError` — לא **403**); שאר Axios errors בודקים סמן `__sentryCaptured` ולא לוכדים פעמיים. cancellation (`ERR_CANCELED`) מדולג בשתי השכבות. |
| **Query key convention** | factories typed ב־[`frontend/src/api/queryKeys.ts`](../../frontend/src/api/queryKeys.ts): `qk` ל-queries, `mk` ל-mutations; שימוש ב-`Record<string, unknown>` לפילטרים לשיפור יציבות טיפוסית והפחתת key drift. |
| **Error ownership** | Axios interceptor = transport/server failures; Query/Mutation cache = fallback capture עם context של request lifecycle; ErrorBoundary = render/runtime errors בלבד. |
| **למה** | מונע פיצול policy בין hooks/קומפוננטות, משפר cache consistency, ומוריד רעש observability (no double-capture). |
| **Trade-off** | שכבת תשתית נוספת בפרונט ודורשת משמעת שימוש ב-query key factories; mis-keying עדיין אפשרי בלי code review/ESLint rules. |
| **בקצרה לראיון** | "בנינו QueryClient מרכזי עם retry policy מבוסס HTTP semantics, dedup לסנטרי בין interceptor ל-React Query, ו-factories אחידים ל-query keys כדי לשמור cache עקבי בסקייל." |

---

## 14. Auth forms standardization (react-hook-form + zod)

| | |
|--|--|
| **הקשר** | מסכי auth (`Login`/`Register`/`VerifyEmail`) נוהלו בחלקם ידנית עם `useState`, מה שהוביל ליותר boilerplate ופחות עקביות ב-validation/submit semantics. |
| **החלטה** | לאמץ `react-hook-form` + `zodResolver` בשלושת המסכים: `loginSchema`, `registerSchema` (כולל password-confirm refine), ו-`verifyEmailSchema` (code מספרי באורך 6). |
| **גבולות החלטה** | לא משנים מבנה JSX/CSS או auth logic (API calls + `navigate` flow) — רק שכבת ניהול מצב הטופס וה-submit. |
| **Behavior parity** | ב-`Login` נשמר `defaultValues` מ-`location.state?.email`; ב-`Register` שדה `PhoneInput` מנוהל דרך `Controller`; ב-`VerifyEmail` `resendLoading` נשאר state נפרד, ו-`isSubmitting` שייך לפעולת verify בלבד. |
| **Error ownership** | validation נשארת בתוך RHF+Zod; שגיאות API נשארות ב-`error` state נפרד ומוצגות ב-`ErrorBanner`/inline error slots כמו קודם. |
| **למה** | עקביות בין מסכי auth, תחזוקה קלה יותר, והפרדת אחריות נקייה בין schema validation לשגיאות transport. |
| **Trade-off** | תלות נוספת ונדרש discipline לשמור schema/field names מסונכרנים לאורך זמן. |
| **בקצרה לראיון** | "סטנדרטנו את כל מסכי ה-auth סביב RHF+Zod בלי לשנות UX או flows — פחות boilerplate, validation אמין יותר, ואותו behavior למשתמש." |

---

## 15. React Query migration Stage 3b (GroupContext + MyRides)

| | |
|--|--|
| **הקשר** | לאחר תשתית RQ (ADR §13), נותרו שני מוקדי state ידני: `GroupContext` ו-`MyRides`, כולל fetch ידני ועדכוני WS דרך `setState`. |
| **החלטה** | להעביר את `GroupContext` ל-`useQuery(qk.groups.list)` עם `enabled: isAuthenticated` ו-`refreshGroups` מבוסס invalidate; להעביר את `MyRides` ל-`useQuery(qk.rides.list)` + `useMutation(mk.rides.cancel)`. |
| **Realtime policy** | במקום patch ידני על state מקומי לכל אירוע, hooks של WS מבצעים `invalidateQueries` על `qk.rides.list` עבור אירועי ride lifecycle. |
| **גבולות** | לא לשנות public API של `useGroup()`, לא לשנות JSX/CSS/UX, ולהשאיר `activeChipId`/`rideToCancel` ב-`useState`. |
| **למה** | מפחית coupling בין transport events לבין UI state, משפר cache consistency, ושומר migration incremental עם סיכון נמוך לרגרסיות. |
| **Trade-off** | יותר תלות ב-cache semantics ו-invalidation discipline; requires code-review vigilance על query keys. |
| **בקצרה לראיון** | "אחרי שהקמנו QueryClient, השלמנו migration למסכים כבדים: Groups ו-MyRides. העברנו fetch/mutation ל-RQ ושינינו WS updates ל-invalidate דטרמיניסטי — אותה חוויית משתמש, פחות state management ידני." |

---

## 16. Web Vitals D — Sentry RUM + metrics (production-only)

| | |
|--|--|
| **הקשר** | ניטור שגיאות בלבד לא נותן תמונת UX מלאה. נדרש למדוד איכות חוויית משתמש בזמן אמת (Core Web Vitals) ולקשר אותה לסשן/משתמש בסביבת production. |
| **החלטה** | להרחיב את `Sentry.init` ב-[`frontend/src/main.tsx`](../../frontend/src/main.tsx) רק תחת `import.meta.env.PROD && APP_CONFIG.sentry.dsn` עם `browserTracingIntegration` + `replayIntegration`, sampling שמרני (`replaysSessionSampleRate: 0.05`, `replaysOnErrorSampleRate: 1.0`), ודיווח `CLS`/`LCP`/`INP` דרך dynamic import של `web-vitals`. |
| **Identity alignment** | ב-[`frontend/src/context/AuthContext.tsx`](../../frontend/src/context/AuthContext.tsx) מתבצע `Sentry.setUser` ב-bootstrap/login/google-login ו-`Sentry.setUser(null)` בכל teardown מוסכם (כולל `session-expired`/`bootstrap-failed`), ראו §21 מטה. |
| **למה** | נותן observability end-to-end של ביצועים אמיתיים אצל משתמשים בפרודקשן, תוך שמירה על פרטיות (`maskAllText`, `blockAllMedia`) ועל quota בעזרת sampling. |
| **Trade-off** | מוסיף תלות telemetry נוספת ועלול להגדיל ingest אם sampling יעלה; לכן נשמרה הפעלה לפרודקשן בלבד ודיווח web-vitals נטען דינמית כדי לצמצם השפעה על bundle. |
| **בקצרה לראיון** | "הוספנו RUM אמיתי: Trace + Replay + Web Vitals בפרודקשן, עם sampling זהיר ו-user context מה-auth flow, כדי למדוד UX אמיתי בלי להכביד על ה-bundle." |

---

## 17. OpenAPI snapshot codegen with Orval (committed generated client)

| | |
|--|--|
| **הקשר** | שכבת API ידנית בפרונט גדלה במהירות ומייצרת סיכון ל-contract drift מול backend. |
| **החלטה** | לאמץ Orval עם snapshot מקומי (`frontend/openapi-snapshot.json`) ולייצר `client/types` לתיקיית `frontend/src/api/generated`, עם mutator אחיד `apiMutator` מעל ה-axios instance הקיים. |
| **Source of truth policy** | קבצי generated נכנסים ל-git במכוון כדי שכל שינוי API יהיה reviewable כחלק מה-PR. |
| **למה** | סוגר פערים בין schema לקוד לקוח, מוריד boilerplate ידני, ומחזק type-safety מקצה לקצה. |
| **Trade-off** | מוסיף שלב generation לתהליך הפיתוח ומאריך מעט את זמן CI, אבל מצמצם משמעותית סיכון ל-contract drift. |
| **CI enforcement (Stage 1, deprecated)** | ב-`frontend-ci` היה job `contract-codegen` שמריץ `npm run gen:api` ואז `git diff --exit-code -- src/api/generated/`. החיסרון: ה-snapshot עצמו היה committed ויכל לסטות בשקט מ-`app.openapi()`; אכיפה הייתה רק על תוצר Orval. |
| **CI enforcement (Stage 2, current)** | ה-snapshot **לא מקומיט** יותר (gitignored כ-build artifact). Workflow ייעודי [`openapi-contract.yml`](../../.github/workflows/openapi-contract.yml) מייצא טרי מ-`app.openapi()` בכל ריצה דרך [`backend/scripts/export_openapi.py`](../../backend/scripts/export_openapi.py), ואז `gen:api`, ואז `git diff --exit-code -- frontend/src/api/generated/`. שינוי schema ב-FastAPI שלא הופעל בפרונט מפיל את ה-PR. ה-job `contract-codegen` הוסר מ-`frontend-ci`. ללא Postgres ב-CI — `app.openapi()` lazy. DX מקומי: `make openapi` / `npm run openapi:sync`. |
| **בקצרה לראיון** | "עברנו מ-API types ידניים ל-codegen חוזי עם Orval, ובסטייג' 2 הסרנו את ה-snapshot מ-git: ה-CI מייצא טרי מ-FastAPI בכל ריצה ובודק drift רק על התוצר הנצרך — מקור אמת יחיד, אין כפילות snapshot↔FastAPI." |

---

## 18. Route-level a11y semantics + GIS module-level singleton

| | |
|--|--|
| **הקשר** | שני anti-patterns חיו ביחד: (1) `h1` גנרי ("LinkUp") ברמת route shell יצר כפילות heading + headings לא אינפורמטיביים; loading states (`Suspense fallback`, `ProtectedRoute` while authenticating) רנדרו `<div>` חשוף בלי landmark/h1, מה שגרם ל-axe לדווח שלוש אזהרות (`landmark-one-main`, `page-has-heading-one`, `region`) בכל מעבר route. (2) Google Identity Services נוהל בתוך React `useEffect` עם cleanup שאיפס `initializedRef` — זה גרם ל-`google.accounts.id.initialize()` להיקרא פעמיים תחת StrictMode dev double-mount, וכל race condition סביב origin/clientId היה מוכפל ב-console. |
| **החלטה** | (1) **a11y**: להסיר `h1` גנרי מ-shells (`PublicPageShell` + `Layout`); כל route מקבל `h1` ייעודי (ויזואלי או `.sr-only`) ו-[`usePageTitle`](../../frontend/src/hooks/usePageTitle.ts) פר-עמוד; [`PageLoading`](../../frontend/src/components/PageLoading/PageLoading.tsx) הוא דף a11y מלא בעצמו (`<main aria-busy aria-live>` + `<h1 sr-only>` + i18n `common:loading`); `ProtectedRoute` משתמש ב-`<PageLoading />` ולא ב-`<div>` חשוף. (2) **GSI**: ה-script-load ו-`initialize()` הורמו למודול singleton ב-[`gisLoader.ts`](../../frontend/src/components/GoogleSignIn/gisLoader.ts) (`loadScriptOnce`, `ensureGisInitialized`, `setGisCredentialHandler`). [`useGoogleSignInScript`](../../frontend/src/components/GoogleSignIn/useGoogleSignInScript.ts) הפך ל-React adapter דק שמסתפק ב-subscribe ל-singleton; cleanup לא מאפס דבר. נוסף DEV-only pre-flight log ב-[`main.tsx`](../../frontend/src/main.tsx) שמדפיס clientId+origin אפקטיביים והוראות diagnose ל-403. ההחלטה על split client-id לפי סביבה (`VITE_GOOGLE_CLIENT_ID`) נשמרה. |
| **למה** | a11y: כל פריים שהמשתמש רואה הוא דף שלם — גם בזמן loading. axe מפסיק לדווח. GSI: GIS היא מערכת ברמת ה-document (script tag, `window.google`, init יחיד), אז הניהול שלה צריך להיות module-scoped ולא בתוך React effect שכל מציאות בורחת ממנו. singleton idempotent מבטל double-init תחת StrictMode וגם תחת re-render של parent עם `onError` לא ממומוז. ה-pre-flight diagnostic מוציא את 403 מקטגוריית "מסתורי" — המפתח רואה מיד את ה-clientId/origin האפקטיביים ומה לבדוק ב-Console. |
| **Trade-off** | a11y: כל route חדש חייב heading ייעודי + `usePageTitle`; ללא guardrails (eslint/a11y CI) regression יכול לחזור. GSI: ה-singleton הוא state גלובלי במודול — אם בעתיד יהיה צורך ברב-clientId באותו דף (לא מתוכנן), הוא ידרוש extension. |
| **בקצרה לראיון** | "loading states הם דפים בפני עצמם — `<main aria-busy>` + sr-only h1; ו-GSI עברה למודול singleton idempotent ש-StrictMode-safe by design — pre-flight log חושף 403 origin mismatch מיד במקום אחרי debugging ארוך." |

---

## 19. Admin data-layer rebuild to domain RQ hooks (remove `useAdminFetch`)

| | |
|--|--|
| **הקשר** | שכבת admin נשענה על helper כללי (`useAdminFetch`) שהקשה על ownership ברור ל-cache/mutations בכל entity. |
| **החלטה** | להחליף ל-hooks ייעודיים לפי דומיין תחת `features/admin/queries` ו-`features/admin/mutations` (`Users`, `Rides`, `Groups`, `Outbox`, `Health`, `Stats`), ולבטל שימוש ב-`useAdminFetch` בקוד admin. |
| **למה** | key ownership ברור, invalidation ממוקד, ויכולת להרחיב דומיין admin בלי side-effects רוחביים. |
| **Trade-off** | יותר קבצים ודפוס boilerplate בין entities, אבל עם גבולות תחזוקה טובים יותר. |
| **בקצרה לראיון** | "ב-admin עברנו מ-helper כללי ל-hooks פר-entity; זה שיפר ownership של cache ומנע coupling בין מסכים." |

---

## 20. Client-side throttle + bundle-budget guardrails

| | |
|--|--|
| **הקשר** | פעולות UI מקבילות יכלו לייצר bursts ל-client network layer, ובמקביל נדרש פיקוח טוב יותר על גידול bundle לאורך שדרוגי frontend. |
| **החלטה** | להוסיף token-bucket throttle ב-`src/api/throttle.ts` ולחבר אותו כאינטרספטור ראשון ב-`src/api/client.ts`; בנוסף להטמיע guardrails של bundle budget (`rollup-plugin-visualizer`, `size-limit`, ו-`manualChunks` ב-`vite.config.ts`). |
| **למה** | throttle ממתן spikes מצד הדפדפן ומשפר יציבות perceived-latency; bundle guardrails הופכים גדילה לא מבוקרת לנראית ומדידה ב-PR/CI. |
| **Trade-off** | throttle אגרסיבי מדי יכול להאט פעולות לגיטימיות; חלוקת chunks דורשת תחזוקה תקופתית כדי לא ליצור fragmentation לא יעיל. |
| **בקצרה לראיון** | "שילבנו token-bucket בצד הלקוח כדי למתן bursts, ובמקביל קבענו תקציב bundle מדיד עם visualizer ו-size-limit." |

---

## 21. Auth session teardown — מקור אמת אחד + `CustomEvent`

| | |
|--|--|
| **בעיה** | לוגיקת ניתוק **הייתה כפולה** בין **logout**, טעינת משתמש נכשלת, ו-**axios refresh** שנכשל ב-**`client`** בלי עדכון React — **`authenticated state` בסטלה (stale)**. |
| **החלטה** | פונקציה **`tearDownSession({ reason })`** ב-[`AuthContext.tsx`](../../frontend/src/context/AuthContext.tsx): **`user-action`** — `patchFcmToken(null)`, `logoutSession()`, אחר כך **תמיד** `cleanupFCM`, `queryClient.clear()`, **`Sentry.setUser(null)`** (ב-PROD), `clearTokens`, `setState` לא מאומת. **`session-expired`** / **`bootstrap-failed`** — ללא PATCH/logout מהשרת, אותם שלבי ניקוי מקומיים. ברמת רשת: [`client.ts`](../../frontend/src/api/client.ts) בשגיאות refresh משגר **`window.dispatchEvent(new Event('auth:session-expired'))`** אחרי `clearTokens`, עם **`emitSessionExpired`** ו-reentrancy guard; גם כשאין **refresh ב-LS** (תיקון באג orphaned access שנשאר). Listener ב-AuthContext מאזין ל-`'auth:session-expired'` וקורא `tearDownSession({ reason: 'session-expired' })`. **`ProtectedRoute`** מפנה ל-`/login?from=` כשהמשתמש **אינו מאומת** — ללא שינוי ב-router. |
| **למה CustomEvent ולא זרימה ל-`logout()` מה-interceptor** | ה-client בשכבה נפרדת — מנותק מתלות קדימית ל-React; מאפשר teardown אחיד בלי import מעגלי ובלי stale closures. |
| **לא נכלל** | PATCH FCM מהנתיב **session-expired** (במכוון; מונע לולאת 401; עדכון DB ב-Re-login מה-Firebase token הקיים למשתמש שחזר); ניקוי **NotRegistered** ב-push — ארוך טווח ב-backend אם צריך. |
| **בקצרה לראיון** | "איחדתי שני מוחות: Axios מפשט tokens ומתריע ב-event חד פעם; Provider מנהל משתמש, cache ו-FCM. שורה רעה בסנטרי — 401 ב-queries מסוננת, 403 לא." |

---

## 22. Open redirect protection on post-login navigation

| | |
|--|--|
| **הקשר** | אחרי login/Google Sign-In, הקוד קורא את `?from=` מה-URL ומפנה אליו. תוקף יכול להזריק `?from=https://evil.com` או `?from=//evil.com` ולהפנות משתמש אחרי התחברות מוצלחת. |
| **החלטה** | לפני `navigate(decoded)`, לוודא `decoded.startsWith('/') && !decoded.startsWith('//')`. ב-`Login.tsx` — כישלון מפיל לשרשרת fallback (`fromState` → `/choose-destination`). ב-`useGoogleSignIn.ts` — גרסה נקייה עם `let target = '/choose-destination'` שמבטיחה navigate תמיד. |
| **למה** | Open redirect הוא OWASP Top 10 (Unvalidated Redirects); גם אם `react-router` navigate לא תמיד מפנה חיצונית, best practice דורש validation בכל מקרה. |
| **Trade-off** | אם `from` לא עומד בתנאי — המשתמש נוחת על דף ברירת מחדל במקום היעד המבוקש. זה מצב נדיר שלא אמור לקרות עם לינקים לגיטימיים מתוך האפליקציה. |
| **בקצרה לראיון** | "מנענו open redirect אחרי login/Google Sign-In — `from` חייב להתחיל ב-`/` ולא ב-`//` כדי למנוע protocol-relative URLs." |

---

## קישורים

- [README.md](README.md) (מפת ADR)  
- [../architecture/REALTIME.md](../architecture/REALTIME.md)  
- [../ERRORS.md](../ERRORS.md)
