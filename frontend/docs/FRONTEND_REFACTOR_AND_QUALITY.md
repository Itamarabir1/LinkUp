# פרונט LinkUp — ריפקטור ואיכות (מקור אמת אחד)

מסמך זה אמור להחליף רשימות חלקיות בשיחות: **כאן** רשומים כל צירי העבודה הרלוונטיים, סטטוס משוער, וקריטריון "סיימנו".  
עדכנו את העמודות ✅ / ⬜ כשמשהו משתנה.

**מקרא:** ✅ בוצע · 🟡 חלקי · ⬜ לא בוצע · — לא רלוונטי

---

## 1. שכבת API (`src/api/`)

**עקרון:** כל קריאת HTTP ממוסגרת בפונקציה ב־`api/<תחום>.ts`; קומפוננטות/הוקים לא ייבאו `api` מ־`client` ישירות (חוץ מ־`client.ts` עצמו).

| אזור | קבצים | סטטוס |
|------|--------|--------|
| אימות מייל | `api/auth.ts` ← `VerifyEmail.tsx` | ✅ |
| בקשות נוסע | `api/passengers.ts` ← `MyRequests.tsx`, `useSearchRides.ts` | ✅ |
| חיפוש נסיעות | `passengers` + `rides` + `geo` ב־`useSearchRides`; join מחיפוש + idempotency ב־`useJoinRide.ts` | ✅ |
| צ'אט (REST) | `api/chat.ts` ← MessageThread, ChatPopup, Messages, `useMyBookings`; **`useMessageThread`/`useChatPopup`** — `Idempotency-Key` יציב (**`outboundIdempotencyKey`**) + רשימת **`ChatListRow`** (אופטימי) + **`applyInboundRealMessage`** / **`appendMessageDedupById`** מול REST ו-WS | ✅ |
| התראות / unread | `users.fetchMyNotifications` + `chat.fetchUnreadMessageCount` ב־`ChatContext`; פיד חי — `useChatNotificationsWebSocket` (`useReconnectingWebSocket`, **`onOpen`** מרענן פיד + unread); גיבוי — `useChatNotificationsFeed` (polling REST ~5 דקות) | ✅ |
| מיקום | `bookings.postDriverBookingLocation` / `postPassengerBookingLocation`; טעינת רשימת נהג: `fetchDriverBookingSummary` (מחליף N+1 של מניפסטים); מניפסט לנסיעה בודדת — `fetchRideManifest` אם נדרש. הוקים `useLocationBroadcast`, `usePassengerLocationBroadcast`, `useLocationWatcher` (throttle 1.5s, `maximumAge: 0`); WS `useDriverLocation`, `usePassengerLocations`; `useMapMarker` + `LiveMapModal` / `LiveRideMapModal` | ✅ |
| הזמנות שלי (REST) | `fetchPassengerBookingSummary`, `fetchDriverBookingSummary` ב־`api/bookings.ts`; הוקים `useMyBookingsPassenger`, `useMyBookingsDriver`; VM מקונן ב־`useMyBookings` + `PassengerBookingCard` | ✅ |
| WebSocket read | `chat.markConversationRead` (כולל `useChatWebSocket`) | ✅ |
| מפתח מפות | `geo.fetchMapsKey` ב־`useGoogleMapsKey` (וב־`RouteMapModal`) | ✅ |
| FCM | `users.patchFcmToken` ← `fcm.ts`, `useFCMCheck` | ✅ |
| Auth / טוקנים | `api/auth.ts` + `users.fetchCurrentUser`; `setTokens`/`clearTokens` מ־`client` ב־`AuthContext` | ✅ |
| נוכחות שותף | `api/presence.ts` — טעינה חד־פעמית ב־`useMessageThread` + WS `user_online`/`user_offline` | ✅ |

**חריגים מותרים ל־`client`:** קבצים תחת `src/api/*`, `AuthContext` (טוקנים בלבד), `api/presence.ts` (מופע `chatWsApi`).

---

## 2. טיפול בשגיאות (`utils/apiError.ts`)

| משימה | סטטוס |
|--------|--------|
| הודעות משתמש דרך `getApiErrorMessage` | ✅ ברוב הזרימות; סריקה חוזרת אחרי פיצ'רים חדשים |
| סטטוס / קוד דרך `getApiStatus`, `getApiErrorCode` | 🟡 |
| Timeout דרך `isTimeoutOrAbortError` | ✅ |
| בדיקות Vitest ל־`apiError` | ✅ |

---

## 3. ניתוב ו־bundle

| משימה | סטטוס |
|--------|--------|
| `React.lazy` + `Suspense` לדפים (כמעט כל ה־routes) | ✅ |
| fallback טעינה (`PageLoading` + מחלקה ב־`App.module.css` ל־ProtectedRoute) | ✅ |
| ניתוח `vite build --report` / visualizer | ⬜ אופציונלי |

---

## 4. ארכיטקטורת state

| רכיב | סטטוס |
|------|--------|
| `ChatContext` + `chatReducer` + `useChatNotificationsFeed` + `useChatNotificationsWebSocket` (פיד התראות מסונכרן עם מצב צ’אט; WS ראשי, poll גיבוי) | ✅ |
| `AuthContext` פיצול שירות session נפרד | ⬜ אופציונלי |
| `GroupContext` — `myGroups`, **`activeChipId`** משותף ל־MyRides/MyRequests, `refreshGroups`; איפוס צ’יפ אחרי leave/close ב־`useGroupManageMutations` | ✅ |

---

## 5. דפים והוקים

| אזור | סטטוס |
|------|--------|
| CreateRide / Profile / Notifications / FCMCheck / Layout / ChatPopup / MessageThread / GroupManage / **MyBookings** (טאב נהג+נוסע, סיכומים מאוגדים, מפה חיה + GPS, `PassengerBookingCard`) / **MyRequests + `useMyRequests`** / GoogleSignIn | ✅ |

---

## 6. עיצוב (CSS)

| משימה | סטטוס |
|--------|--------|
| אינליין הוסר מ־`Login`, `Register`, `VerifyEmail`; מסך טעינה ב־`App` | ✅ |
| `tokens.css` גלובלי + `data-theme` / `ThemeProvider` / כפתור מצב כהה | ✅ |

---

## 7. בדיקות

| משימה | סטטוס |
|--------|--------|
| Vitest | ✅ |
| `apiError`, `chatReducer`, `myBookings.utils`, MessageThread WS, `ErrorBanner` | ✅ |
| Playwright | ⬜ החלטת מוצר |

---

## 8–10. a11y, אבטחה, תיעוד

| משימה | סטטוס |
|--------|--------|
| a11y מלא | 🟡 |
| `.env.example` / XSS | 🟡 |
| `ARCHITECTURE.md` + מסמך זה | ✅ |

---

## מתי נחשב "סיימנו ריפקטור פרונט"?

1. ✅ שכבת API ממוסגרת (עם חריגים מתועדים למעלה).  
2. ✅ Lazy loading לדפים.  
3. ✅ דפי auth + מסך טעינה בלי אינליין "ארוך".  
4. ✅ בדיקות יחידה ל־utils/reducer קריטיים.  
5. ✅ מסמך זה מעודכן.

---

## מחוץ להיקף

- שכתוב מלא ל־RSC · החלפת ספריית UI · i18n מלא — רק לפי החלטת מוצר.

---

## איך משתמשים במסמך הזה

1. שינוי ארכיטקטורה — עדכן טבלאות למעלה.  
2. ל־AI: "בצע לפי `FRONTEND_REFACTOR_AND_QUALITY.md` סעיף X".
