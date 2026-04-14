# Linkup — שישה פרומפטים (בקאנד + פרונט) וסדר הרצה

## סדר הרצה מומלץ (כפי שהגדרת)

**בקאנד (עצמאיים זה מזה, אפשר PR נפרדים):**

1. **פרומפט 1** — `GET /bookings/driver-summary` (N+1 נהג)
2. **פרומפט 2** — `GET /bookings/passenger-summary` (N+1 נוסע)
3. **פרומפט 3** — העברת `report_driver_location` / `report_passenger_location` ל-`BookingService`
6. **פרומפט 6** — try/except + rollback עקבי ב-`approve_booking` / `reject_booking` / `cancel_booking` + הסרת הערה stale ב-`crud.py`

**פרונט (אחרי בקאנד או במקביל ל-API חדש כשמוכן):**

4. **פרומפט 4** — חילוץ `PassengerBookingCard` מ-`PassengerBookingsTab`
5. **פרומפט 5** — `useMyBookings` מחזיר אובייקט מקונן + `MyBookingsViewModel`

**הערה:** 1→2→3→6 בבקאנד לא חייבים להיות ברצף יום אחד; 4→5 בפרונט — 4 לפני 5 מפחית “רעש” ב-diff (קומפוננטה יציבה ואז שינוי צורת ה-vm).

---

## מפת פרומפטים

| # | תחום | מטרה | קבצים עיקריים |
|---|------|------|----------------|
| 1 | Backend | אגרגציית נהג בשאילתה אחת | `bookings/schema.py`, `crud.py`, `service.py`, `router.py` |
| 2 | Backend | אגרגציית נוסע בשאילתה אחת | אותם תחת `bookings/` |
| 3 | Backend | Router רזה למיקום | `service.py`, `router.py` |
| 4 | Frontend | קומפוננטת כרטיס נוסע | `PassengerBookingCard.tsx` (חדש), `PassengerBookingsTab.tsx` |
| 5 | Frontend | vm מקונן | `useMyBookings.ts`, `index.tsx` (+ מיפוי props לטאבים) |
| 6 | Backend | עקביות rollback/לוגים | `service.py`, `crud.py` |

לאחר 1–2: לעדכן פרונט (`useMyBookingsDriver` / `useMyBookingsPassenger`) כדי לממש את יתרון ה-N+1 — זה שלב נפרד מהפרומפטים האלה אבל תלוי API.

---

## פרומפט 4 — PassengerBookingCard

- **מטרה:** קריאות, בדיקות, חוזה props ברור; הפחתת פונקציה אנונימית חדשה בכל רנדר (השפעה תלוית-memoization של הורה).
- **איכות:** תואם React סטנדרטי; props רחבים — אחרי פרומפט 5 אפשר (אופציונלי) להעביר `vm.passenger` חתוך כדי לצמצם רשימת props.
- **סיכונים:** נמוכים — refactor טהור אם ה-JSX זהה.

---

## פרומפט 5 — useMyBookings מקונן

- **מטרה:** קריאות, גבולות דומיין (passenger / driver / chat), טיפוס יצוא `MyBookingsViewModel`.
- **היקף שינוי:** בפרויקט הנוכחי רק [`frontend/src/pages/MyBookings/index.tsx`](frontend/src/pages/MyBookings/index.tsx) קורא ל-`useMyBookings()` — עדכון שם + טאבים **אופציונלי**: מומלץ להשאיר חתימות `PassengerBookingsTab` / `DriverBookingsTab` כמו היום ולמפות מ-`vm.passenger.*` / `vm.driver.*` / `vm.chat.*` ב-`index.tsx` (פחות קבצים משתנים).
- **סיכונים:** נמוכים; לוודא `ReturnType<typeof useMyBookings>` לא חושף שדות פנימיים מיותרים אם מייצאים לצרכנים עתידיים.

---

## פרומפט 6 — Error handling ב-BookingService

- **מטרה:** מניעת סשן DB “מלוכלך” אחרי כשל לא צפוי ב-commit; עקביות עם `request_to_join`.
- **התנהגות:** ללקוח HTTP — אותם סטטוסים אם אותן חריגות; על שגיאות לא צפויות — עדיין 500, אבל עם rollback (שיפור, לא שבירה של contract).
- **אימות:** קיים הערה מיותרת ב-[`backend/app/domain/bookings/crud.py`](backend/app/domain/bookings/crud.py) סביב שורה 388 — הסרה מתאימה.
- **אופציונלי (מחוץ לפרומפט):** ב-`except Exception` להוסיף `exc_info=True` ל-`logger.error` לניפוי עומק, בלי לשנות סטטוסים.

---

## תלויות ותיעוד

- Endpoints חדשים (1–2) ושינוי API docs — לפי `.cursor/rules/architecture-sync.mdc` → `docs/architecture/API.md`.
- בדיקות: להרחיב/להוסיף ב-`backend/tests/` ל-endpoints החדשים; לפרונט — `npx tsc --noEmit` כנדרש בפרומפטים.

---

## סטטוס TODO (מעקב)

- [ ] פרומפט 1 — driver-summary
- [ ] פרומפט 2 — passenger-summary
- [ ] פרומפט 3 — broadcast → service
- [ ] פרומפט 4 — PassengerBookingCard
- [ ] פרומפט 5 — vm מקונן
- [ ] פרומפט 6 — rollback + לוגים + crud comment
- [ ] (שלב נפרד) חיווט פרונט ל-endpoints 1–2

---

## חוות דעת קצרה על ההוספות (4–6)

כל שלושתם **נכונות ומומלצות** ברמת סניור: 4–5 משפרות תחזוקה בלי לגעת בלוגיקת דומיין; 6 מתקנת מחלקת בעיה אמיתית ב-SQLAlchemy (טרנזקציות). סדר **בקאנד לפני פרונט** הגיוני כי ה-API המאוחד (1–2) משחרר את ה-N+1 בשרת; 4–5 לא תלויים ב-API אבל עדיף לא לערבב גדולי refactor ב-PR אחד. **6 אחרי 3** מתאים כי שניהם נוגעים ל-`BookingService`/`router` — אפשר גם לפני 3 אם רוצים לצמצם merge conflicts (שניהם לגיטימיים).
