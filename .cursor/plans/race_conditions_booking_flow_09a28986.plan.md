---
name: Race Conditions Booking Flow
overview: דיווח על שלושת הסימני שאלה בזרימת ההזמנות, תכנית תיקונים (נעילות כבר קיימות; נדרש רק תיקון ב-execute_booking_cancellation כשהנסיעה כבר CANCELLED), ויישום רק אחרי אישור.
todos: []
isProject: false
---

# בדיקה ותיקון Race Conditions בזרימת הזמנות

## שלב 1 — תשובות לסימני השאלה

### 1.1 `cancel_booking` — האם מונע ביטול של CONFIRMED / REJECTED?

**קוד נוכחי** ([backend/app/domain/bookings/service.py](backend/app/domain/bookings/service.py) שורות 335–349):

- בודק רק: booking קיים, המשתמש הוא נוסע או נהג. **אין** בדיקת סטטוס של ההזמנה לפני הביטול.
- **לא** מונע ביטול של booking במצב CONFIRMED — ומכוון: נוסע/נהג אמורים לאפשר ביטול גם אחרי אישור.
- **לא** מונע ביטול של booking במצב REJECTED — מבחינת לוגיקה ביטול של נדחה רק מעדכן ל-CANCELLED (תקין).

**Race:** אם נוסע מבטל ובה־בעת הנהג מאשר — שני ה־`_sync` רצים; אחד עם נעילת נסיעה. מי שננעל ראשון מעדכן; השני רואה מצב מעודכן. **הנעילה כבר קיימת** (שורות 344–347: `get_ride_for_update` לפני `execute_booking_cancellation`), ולכן התרחיש מטופל.

**מסקנה:** אין להוסיף חסימת ביטול ל-CONFIRMED; הלוגיקה הנוכחית נכונה. אין צורך בשינוי.

---

### 1.2 `execute_booking_cancellation` — החזרת מושבים וסטטוס נסיעה

**קוד נוכחי** ([backend/app/domain/bookings/crud.py](backend/app/domain/bookings/crud.py) שורות 209–219):

```python
def execute_booking_cancellation(self, db: Session, booking: Booking):
    if booking.status == BookingStatus.CONFIRMED:
        ride = booking.ride
        ride.available_seats += booking.num_seats
        ride.status = RideStatus.OPEN
    booking.status = BookingStatus.CANCELLED
    ...
```

- מחזיר `available_seats` רק כש־booking היה CONFIRMED — תקין.
- תמיד מגדיר `ride.status = RideStatus.OPEN` כשמחזירים מושבים — **בעייתי**: אם הנסיעה כבר בוטלה על ידי הנהג (`ride.status == CANCELLED`), לא צריך להחזיר אותה ל-OPEN.

**תרחיש:** נהג מבטל נסיעה (ride → CANCELLED), ובה־בעת או אחר כך נוסע מבטל את ההזמנה שלו. ב־`execute_booking_cancellation` אנחנו קוראים `ride.status = RideStatus.OPEN` ודורסים את CANCELLED.

**מסקנה:** יש לתקן — להחזיר ל-OPEN רק כאשר הנסיעה לא במצב CANCELLED (למשל: `if ride.available_seats > 0 and ride.status != RideStatus.CANCELLED: ride.status = RideStatus.OPEN` או בדיקה דומה).

---

### 1.3 `cancel_ride_and_all_bookings` / `_cancel_ride_sync` — PENDING ונעילה

**קוד נוכחי** ([backend/app/domain/bookings/service.py](backend/app/domain/bookings/service.py) שורות 72–99):

- `_cancel_ride_sync` קורא ל־`crud_booking.bulk_update_bookings_status(sess, ride_id, BookingStatus.CANCELLED)` — מעדכן **כל** ה-bookings של הנסיעה ל-CANCELLED (כולל PENDING).
- אין ב־`_cancel_ride_sync` עצמו `get_ride_for_update`; הנעילה מתבצעת ב־`cancel_ride_by_driver` ב־[backend/app/domain/rides/service.py](backend/app/domain/rides/service.py): קודם `get_for_update(ride_id, driver_id)` ואז `BookingService.cancel_ride_and_all_bookings(db, ...)` באותה טרנזקציה, כך שנעילת השורה נשמרת עד ה-commit.
- אם נוסע יצר PENDING רגע לפני ביטול: אם הביטול קודם — הנסיעה ו־bookings מתבטלים; `request_to_join` שירוץ אחר כך יראה נסיעה CANCELLED ויזרוק RideNotAvailableError. אם הבקשה קודם — נוצר PENDING ואז הביטול מריץ bulk_update שמבטל גם אותו. בשני המקרים התוצאה עקבית.

**מסקנה:** PENDING מטופל; הנעילה מתבצעת ב־cancel_ride_by_driver. אין צורך בשינוי.

---

## שלב 2 — תכנית תיקונים

### מה כבר קיים (לא לשנות)

- **approve_booking:** כבר קיימת נעילה עם `get_ride_for_update` לפני `execute_booking_approval` (שורות 274–277).
- **cancel_booking:** כבר קיימת נעילה עם `get_ride_for_update` לפני `execute_booking_cancellation` (שורות 344–347).

### שינוי נדרש יחיד

**קובץ:** [backend/app/domain/bookings/crud.py](backend/app/domain/bookings/crud.py)  
**פונקציה:** `execute_booking_cancellation`

**הבעיה:** כשמבטלים הזמנה מאושרת, הקוד תמיד כותב `ride.status = RideStatus.OPEN`. אם הנסיעה כבר בוטלה על ידי הנהג, אסור לדרוס ל-OPEN.

**תיקון מתוכנן (diff):**

```diff
     def execute_booking_cancellation(self, db: Session, booking: Booking):
         if booking.status == BookingStatus.CONFIRMED:
             ride = booking.ride
             ride.available_seats += booking.num_seats
-            ride.status = RideStatus.OPEN
+            if ride.status != RideStatus.CANCELLED:
+                ride.status = RideStatus.OPEN
         booking.status = BookingStatus.CANCELLED
```

**סיכום:** רק קובץ אחד משתנה — `backend/app/domain/bookings/crud.py`. אין צורך בשינוי ב־service (נעילות כבר הוספו בעבר).

---

## שלב 3 — יישום (רק אחרי אישור)

- **לא** להוסיף נעילות ב־approve_booking / cancel_booking — כבר קיימות.
- **לבצע** את ה-diff למעלה ב־`execute_booking_cancellation`: להחזיר נסיעה ל-OPEN רק כאשר היא לא כבר CANCELLED.

---

## דיווח סופי מתוכנן

- **סימני שאלה:** (1) אין חסימת ביטול ל-CONFIRMED — מכוון. (2) יש לתקן דריסת ride.status ל-OPEN כשהנסיעה כבר CANCELLED. (3) PENDING וביטול נסיעה מטופלים; נעילה ב־cancel_ride_by_driver.
- **Diff:** רק ב־crud.py כ� above.
- **תרחיש:** תיקון אחד — מונע שדריסת `ride.status = OPEN` אחרי ביטול נסיעה על ידי הנהג כשנוסע מבטל הזמנה מאושרת.