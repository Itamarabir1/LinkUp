# שינויים ב-rides/crud.py

## מחיקות:

1. הסר את הפונקציה get_expired_ids:
   def get_expired_ids(self, db: Session, now: datetime) -> list:
   (sync, משמשת רק את ride_expiry.py המת)

2. הסר את הפונקציה bulk_set_completed:
   def bulk_set_completed(self, db: Session, ride_ids: list):
   (sync, משמשת רק את ride_expiry.py המת)

3. הסר את הפונקציה get_rides_needing_reminders:
   async def get_rides_needing_reminders(...)
   (מוחלפת ע"י crud_scheduled_notification.get_due)

4. הסר את הפונקציה get_bookings_for_reminders ב-CRUDRide:
   def get_bookings_for_reminders(...)
   (sync, מוחלפת ע"י crud_scheduled_notification.get_due)

## הערה:
get_bookings_for_reminders קיים גם ב-CRUDBooking (bookings/crud.py) — מחק גם שם.
