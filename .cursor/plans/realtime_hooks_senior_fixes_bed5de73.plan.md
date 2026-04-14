---
name: Realtime hooks senior fixes
overview: חוות דעת על חמשת התיקונים, סיכונים, שיפורים אופציונליים, ותכנית יישום בחמישה קבצים + tsc.
todos:
  - id: fix-useUserEvent
    content: useUserEvent.ts — depsKey יציב מ-eventName (מערך ממוין + join)
    status: pending
  - id: fix-MyRides-watched
    content: MyRides.tsx — watchedRideId לפי LIVE_STATUSES + מיון departure_time (הכי מוקדם)
    status: pending
  - id: fix-passenger-ws
    content: useMyBookingsPassenger.ts — LIVE_STATUSES + תיקון הלוגיקה ההפוכה + מיון
    status: pending
  - id: fix-status-label
    content: myBookings.constants.ts — completed בעברית ב-STATUS_LABEL
    status: pending
  - id: fix-driver-comment
    content: useMyBookingsDriver.ts — TODO N+1 מעל Promise.all
    status: pending
  - id: verify-tsc
    content: npx tsc --noEmit (ולאחר מכן eslint אם רלוונטי)
    status: pending
isProject: false
---

# Realtime / hooks — הערכת מפרט + תכנית יישום

## האם התיקונים טובים?


| תיקון                            | הערכה                                                                                                                                                                                           |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — `useUserEvent` deps**      | כן. מערך ליטרלי חדש בכל רינדור שובר `[eventName]` וגורם להרשמה מחדש. `depsKey` ממוין + `join` נותן מפתח פרימיטיבי יציב לאותה קבוצת שמות.                                                        |
| **2 — `MyRides` watchedRideId**  | כן. `find()` = סדר API אקראי; "היציאה הקרובה ביותר" בין נסיעות חיות היא כלל עסקי הגיוני ל-WS אחד.                                                                                               |
| **3 — `useMyBookingsPassenger`** | **קריטי.** הקוד הנוכחי `confirmed && status !== 'active'` פותח WS כשהנסיעה *לא* פעילה — הפוך לצורך (ביטול לפני יציאה, STARTED, וכו'). המעבר ל-`LIVE_STATUSES.has` + מיון תואם את הסיפור שתיארת. |
| **4 — `STATUS_LABEL.completed`** | כן. רק `PassengerBookingsTab` משתמש; אין כפילות עם `getRequestStatusLabel` (דומיין אחר).                                                                                                        |
| **5 — TODO N+1 בנהג**            | כן — תיעוד בלי לשנות API, עומד במגבלות.                                                                                                                                                         |


## מה הייתי עושה אחרת (אופציונלי, לא חובה ב-PR הזה)

- `**LIVE_STATUSES` כפול** — אחרי התיקון יהיה אותו `Set` ב-`MyRides` ו-`useMyBookingsPassenger`. סניור יאחד לקובץ קטן, למשל `frontend/src/constants/rideLiveStatuses.ts` או ליד `wsEvents`, כדי שלא יסטו בעתיד. המפרט שלך אומר "רק 5 קבצים" — אפשר PR נפרד.
- **מיון `departure_time`** — אם שתי נסיעות באותו timestamp, אפשר tie-breaker (`ride_id`) ליציבות; לא חובה.
- **הערות "מעל כל שורה"** — המפרט דורש זה; בפועל מספיק בלוק קצר אחד למעלה ("למה") כדי לא לזהם את הקוד.

## קבצים נוספים לשים לב (בלי לשנות בהכרח)

- `[PassengerBookingsTab.tsx](frontend/src/pages/MyBookings/PassengerBookingsTab.tsx)` — ירוויח מ-`completed` ב-`STATUS_LABEL`; אין שינוי קוד נדרש שם.
- אין צורך לגעת ב-`useRideWebSocket` / `useReconnectingWebSocket` לתיקונים האלה.

## סיכונים

- **עדיין רק WS אחד לנסיעה** — אם יש שתי נסיעות חיות למשתמש (נדיר), רק הראשונה לפי המיון תקבל את ה-WS. זה מודעות מוצרית, לא באג ביישום המפרט.
- `**useUserEvent`** — עם `depsKey` בלבד, ה-`useEffect` חייב לקרוא `eventName` מהסגירה העדכנית כש-`depsKey` משתנה; המימוש המוצע עושה זאת כי כל ריצה מחדש של האפקט לוכדת את `eventName` הנוכחי.

## סדר יישום (מומלץ)

1. `useUserEvent.ts` — תלות יציבה.
2. `useMyBookingsPassenger.ts` — באג פונקציונלי (הפוך).
3. `MyRides.tsx` — בחירת נסיעה לצפייה.
4. `myBookings.constants.ts` — תווית.
5. `useMyBookingsDriver.ts` — הערה בלבד.

אחרי כל קבוצת שינויים: `cd frontend && npx tsc --noEmit`.

## מגבלות מהמפרט שלך

- בלי שינוי UI/CSS/props — נשמר.
- בלי שינוי שמות אירועים / חתימות API — נשמר.

---

**סיכום:** לא סיימתי קודם — המסמך היה ריק מתוכן. עכשיו התכנית המלאה כאן. לביצוע בפועל בקוד, כתוב במפורש "תיישם / execute".