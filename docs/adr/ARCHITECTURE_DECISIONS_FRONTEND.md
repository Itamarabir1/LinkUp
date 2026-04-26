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
| **החלטה** | **צ'אט** דרך **chat-ws** (Go); **נסיעות / מיקום / פיד התראות** דרך **WebSocket של FastAPI** (ראו [WEBSOCKETS.md](WEBSOCKETS.md)). פריימים נכנסים עוברים **Zod** (`safeParse`) ב-[`wsEvents.ts`](../../frontend/src/types/wsEvents.ts) ובעיבוד הודעות צ'אט ב-[`processChatWebSocketMessage.ts`](../../frontend/src/pages/MessageThread/processChatWebSocketMessage.ts). |
| **למה Zod** | חוזה בזמן ריצה מול JSON מהרשת; פחות `as` לא בטוחים; בדיקות יחידה על סכמות. |
| **בקצרה לראיון** | "לא סומכים על צורת JSON מה-WS — מאמתים עם Zod לפני שמעדכנים state." |

---

## 5. פיד התראות in-app — WS + reconnect + polling גיבוי

| | |
|--|--|
| **החלטה** | [`useChatNotificationsWebSocket`](../../frontend/src/context/useChatNotificationsWebSocket.ts) מעל [`useReconnectingWebSocket`](../../frontend/src/hooks/useReconnectingWebSocket.ts); ב-**`onOpen`** (גם אחרי reconnect) — רענון פיד, unread ואירוע `linkup-notifications-refresh`. גיבוי: [`useChatNotificationsFeed`](../../frontend/src/context/useChatNotificationsFeed.ts) — polling REST כל **~5 דקות**. |
| **למה** | אמינות מול רשת ניתקת בלי לרדוף אחרי השרת כל שנייה; איזון בין חוויית "חי" לבין עומס וסוללה. |
| **בקצרה לראיון** | "העדפנו WS ראשי עם רענון אוטומטי אחרי חיבור מחדש, ו-polling דל כגיבוי." |

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
| **החלטה** | `AuthContext`, `ChatContext`, `GroupContext`; לוגיקת צ'אט/התראות מפוצלת ל-hooks קטנים (`useChatUnreadMessages`, וכו'). **הזמנות שלי**: קומפוזיציה ב-[`useMyBookings.ts`](../../frontend/src/pages/MyBookings/useMyBookings.ts) עם **מבנה החזרה מקונן** (`passenger`, `driver`, `chat`) — בלי spread של תוצאות ה-hooks לשטח אחד; יצוא טיפוס **`MyBookingsViewModel`**. נתונים נטענים מ־**endpoints מאוגדים** בבקאנד (`driver-summary` / `passenger-summary`) כדי למנוע N+1. |
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
| **החלטה** | **i18next** + `react-i18next`; משאבים תחת [`frontend/src/i18n/locales/`](../../frontend/src/i18n/locales/) (`he` / `en`), כולל מפתחות **`common:err_*`** לטקסטי שגיאה כלליים. |
| **למה** | מוצר מקומי עם אפשרות הדגמה/שימוש ב-LTR; מחרוזות UI ושגיאות נשארות מתורגמות גם מחוץ לרכיבי React (hooks) דרך `i18n.t`. |
| **בקצרה לראיון** | "לא שומרים עברית קשיחה ב-hooks — מפתחות `common` ו-`apiErr`." |
| **עדכון S.7** | `common`/`nav` נשארים **bundled** ב-`src/i18n/config.ts`, בעוד namespaces פיצ'ריים (`auth`,`rides`,`bookings`,`groups`,`profile`,`billing`) נטענים עצלנית דרך `i18next-http-backend` מ-`/locales/{{lng}}/{{ns}}.json` (מקור אמת נשאר ב-`src/i18n/locales`, והעתקה runtime ב-`public/locales`). |

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
| **Dedup pattern (Sentry)** | ה-axios interceptor מסמן `__sentryCaptured=true` לפני capture ל-5xx; ב-React Query `onError` בודק את הסמן ולא מצלם שוב. cancellation (`ERR_CANCELED`) מדולג בשתי השכבות. |
| **Query key convention** | factories typed ב־[`frontend/src/api/queryKeys.ts`](../../frontend/src/api/queryKeys.ts): `qk` ל-queries, `mk` ל-mutations; שימוש ב-`Record<string, unknown>` לפילטרים לשיפור יציבות טיפוסית והפחתת key drift. |
| **Error ownership** | Axios interceptor = transport/server failures; Query/Mutation cache = fallback capture עם context של request lifecycle; ErrorBoundary = render/runtime errors בלבד. |
| **למה** | מונע פיצול policy בין hooks/קומפוננטות, משפר cache consistency, ומוריד רעש observability (no double-capture). |
| **Trade-off** | שכבת תשתית נוספת בפרונט ודורשת משמעת שימוש ב-query key factories; mis-keying עדיין אפשרי בלי code review/ESLint rules. |
| **בקצרה לראיון** | "בנינו QueryClient מרכזי עם retry policy מבוסס HTTP semantics, dedup לסנטרי בין interceptor ל-React Query, ו-factories אחידים ל-query keys כדי לשמור cache עקבי בסקייל." |

---

## 14. Login form standardization (react-hook-form + zod)

| | |
|--|--|
| **הקשר** | מסך `Login` נוהל ידנית עם `useState` עבור ערכים ו-loading, מה שהוביל ליותר boilerplate ופחות עקביות עם כיוון ארכיטקטורת forms typed בפרונט. |
| **החלטה** | לאמץ `react-hook-form` + `zodResolver` במסך `Login`, עם סכמת `loginSchema` (`email`/`password`) ו-`defaultValues` שמכבדים `location.state?.email` ל-prefill אחרי redirect/verification flow. |
| **גבולות החלטה** | לא משנים מבנה JSX/CSS או auth logic (`login` + `navigate` chain) — רק שכבת ניהול מצב הטופס וה-submit. |
| **Error ownership** | validation נשארת בתוך RHF+Zod; שגיאות API נשארות ב-`error` state נפרד ומוצגות ב-`ErrorBanner` כמו קודם. |
| **למה** | עקביות, תחזוקה קלה יותר, ומוכנות למיגרציה הדרגתית של מסכי auth נוספים לאותו pattern בלי breaking UX. |
| **Trade-off** | תלות נוספת ונדרש discipline לשמור schema/field names מסונכרנים. |
| **בקצרה לראיון** | "השארתי את ה-UX וה-auth flow זהים, והחלפתי רק את שכבת form-state ל-RHF+Zod — פחות boilerplate, יותר correctness, ואותו behavior למשתמש." |

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
| **Identity alignment** | ב-[`frontend/src/context/AuthContext.tsx`](../../frontend/src/context/AuthContext.tsx) מתבצע `Sentry.setUser` ב-bootstrap/login/google-login ו-`Sentry.setUser(null)` ב-logout כדי לשייך traces/replays למשתמש נכון לאורך מחזור האימות. |
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
| **Trade-off** | מוסיף שלב generation לתהליך הפיתוח ודורש gate ב-CI למניעת שכחת regeneration. |
| **בקצרה לראיון** | "עברנו מ-API types ידניים ל-codegen חוזי עם Orval; ה-generated client מחויב ב-repo ונבדק ב-CI כדי למנוע drift בין backend ל-frontend." |

---

## קישורים

- [README.md](README.md) (מפת ADR)  
- [../architecture/REALTIME.md](../architecture/REALTIME.md)  
- [../ERRORS.md](../ERRORS.md)
