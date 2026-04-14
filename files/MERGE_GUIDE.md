# מדריך מיזוג — סדר מדויק

## שלב 1: DB (migration)
backend/alembic/versions/008_scheduled_notifications.py  ← קובץ חדש

## שלב 2: Domain חדש
backend/app/domain/scheduled_notifications/model.py       ← קובץ חדש
backend/app/domain/scheduled_notifications/crud.py        ← קובץ חדש
backend/app/domain/scheduled_notifications/__init__.py    ← ריק (צור ידנית)

## שלב 3: הסרת reminder_sent מ-models
backend/app/domain/rides/model.py      ← הסר שורת reminder_sent (ראה rides_model_diff.md)
backend/app/domain/bookings/model.py   ← הסר שורת reminder_sent (ראה bookings_model_diff.md)

## שלב 4: הסרת sync methods מ-CRUDs
backend/app/domain/rides/crud.py       ← הסר get_expired_ids, bulk_set_completed,
                                          get_rides_needing_reminders, get_bookings_for_reminders
backend/app/domain/bookings/crud.py    ← הסר get_bookings_for_reminders

## שלב 5: מחיקת ride_expiry.py
backend/app/domain/rides/ride_expiry.py  ← מחק את הקובץ

## שלב 6: בקאנד — לוגיקה
backend/app/domain/system/maintenance_crud.py         ← החלף בקובץ החדש
backend/app/domain/system/maintenance_service.py      ← החלף בקובץ החדש
backend/app/workers/tasks/notification_tasks.py       ← החלף בקובץ החדש
backend/app/domain/notifications/services/reminder_scheduler.py ← החלף בקובץ החדש

## שלב 7: Redis infrastructure
backend/app/infrastructure/redis/keys.py              ← החלף בקובץ החדש
backend/app/domain/rides/broadcast.py                 ← החלף בקובץ החדש

## שלב 8: Go
chat-ws/internal/redis/subscriber.go                  ← החלף בקובץ החדש

## שלב 9: פרונט (כל הקבצים מהגרסה הקודמת)
frontend/src/types/wsEvents.ts
frontend/src/hooks/useUserEventStream.ts              ← חדש
frontend/src/components/Layout/useLayoutShell.ts
frontend/src/components/HistorySection/HistorySection.tsx     ← חדש
frontend/src/components/HistorySection/HistorySection.module.css ← חדש
frontend/src/pages/MyRides.tsx
frontend/src/pages/MyRequests.tsx
frontend/src/pages/useMyRequests.ts
frontend/src/pages/MyBookings/index.tsx
frontend/src/pages/MyBookings/PassengerBookingCard.tsx
frontend/src/pages/MyBookings/DriverBookingsTab.tsx
frontend/src/pages/MyBookings/PassengerBookingsTab.tsx
frontend/src/pages/MyBookings/useMyBookings.ts
frontend/src/pages/MyBookings/useMyBookingsDriver.ts
frontend/src/pages/MyBookings/useMyBookingsPassenger.ts
frontend/src/api/bookings.ts

## בדיקות לאחר מיזוג
1. alembic upgrade head — בדוק שה-migration עולה נקי
2. backend tests — pytest tests/ -v
3. בדוק שאין import של reminder_sent בשום מקום
4. בדוק שאין import של ride_expiry בשום מקום
5. בדוק שאין import של get_expired_ids / bulk_set_completed בשום מקום
