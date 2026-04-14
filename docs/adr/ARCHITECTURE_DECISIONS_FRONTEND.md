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
| **בקצרה לראיון** | "מיישרים קו עם LinkupError בבקאנד — קוד שגיאה, הודעה, ו-fallback לפי error_code." |

---

## 10. i18n (עברית + אנגלית)

| | |
|--|--|
| **החלטה** | **i18next** + `react-i18next`; משאבים תחת [`frontend/src/i18n/locales/`](../../frontend/src/i18n/locales/) (`he` / `en`), כולל מפתחות **`common:err_*`** לטקסטי שגיאה כלליים. |
| **למה** | מוצר מקומי עם אפשרות הדגמה/שימוש ב-LTR; מחרוזות UI ושגיאות נשארות מתורגמות גם מחוץ לרכיבי React (hooks) דרך `i18n.t`. |
| **בקצרה לראיון** | "לא שומרים עברית קשיחה ב-hooks — מפתחות `common` ו-`apiErr`." |

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

## קישורים

- [README.md](README.md) (מפת ADR)  
- [../architecture/REALTIME.md](../architecture/REALTIME.md)  
- [../ERRORS.md](../ERRORS.md)
