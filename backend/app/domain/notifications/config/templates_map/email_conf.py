EMAIL_MAP = {
    # --- Driver events ---
    "new_ride_request": {
        "template": "driver/new_ride_request.html",
        "subject": "בקשת הצטרפות לנסיעה",
        "body": "היי {user_name}, {passenger_name} ביקש/ה להצטרף לנסיעה – {ride_date}. איסוף: {pickup_name}, יעד: {passenger_destination}.",
    },
    "passenger_cancelled": {
        "template": "driver/passenger_cancelled.html",
        "subject": "עדכון: נוסע ביטל את הצטרפותו לנסיעה ⚠️",
        "body": "היי {user_name}, נוסע ביטל את השתתפותו בנסיעה ל{destination}.",
    },
    "reminder_driver": {
        "template": "driver/ride_reminder_driver.html",
        "subject": "תזכורת לנהג: יוצאים לדרך בעוד שעה! 🛣️",
        "body": "תזכורת: הנסיעה שלך ל{destination} יוצאת בעוד שעה.",
    },
    # --- Passenger events ---
    "ride_created_for_passengers": {
        "template": "passenger/ride_created_for_passengers.html",
        "subject": "נסיעה חדשה שמתאימה לך – מ{origin} ל{destination} 🚗",
        "body": "היי {user_name}, נרשמה נסיעה מ{origin} ל{destination} שיוצאת ב{ride_date}. לחץ/י לצפייה ובקשת הצטרפות.",
    },
    "booking_confirmed": {
        "template": "passenger/booking_approved.html",
        "subject": "איזה כיף! הנסיעה שלך אושרה ✅",
        "body": "היי {user_name}, הנהג אישר את בקשתך לנסיעה ל{destination}!",
    },
    "booking_rejected": {
        "template": "passenger/booking_rejected.html",
        "subject": "עדכון לגבי בקשת הנסיעה שלך ℹ️",
        "body": "היי {user_name}, לצערנו הבקשה לנסיעה ל{destination} לא אושרה.",
    },
    "ride_cancelled_by_driver": {
        "template": "passenger/ride_cancelled_by_driver.html",
        "subject": "עדכון דחוף: הנסיעה בוטלה על ידי הנהג 🛑",
        "body": "הודעה דחופה: הנסיעה ל{destination} בוטלה על ידי הנהג.",
    },
    "reminder_passenger": {
        "template": "passenger/ride_reminder_passenger.html",
        "subject": "הנסיעה שלך יוצאת בעוד שעה! 🚗",
        "body": "היי {user_name}, תזכורת: הנסיעה שלך ל{destination} יוצאת בעוד שעה.",
    },
    # --- Auth & user lifecycle ---
    "welcome": {
        "template": "user/welcome.html",
        "subject": "ברוכים הבאים ל-LinkUp! 🎉",
        "body": "היי {user_name}, ברוך הבא לקהילת LinkUp! איזה כיף שהצטרפת.",
    },
    "email_verification": {
        "template": "user/verify_email.html",
        "subject": "אימות כתובת המייל שלך - LinkUp 🛡️",
        "body": "קוד האימות שלך ל-LinkUp הוא: {code}",
    },
    "password_reset_code": {
        "template": "user/password_reset.html",
        "subject": "קוד לאיפוס הסיסמה שלך - LinkUp 🔑",
        "body": "הקוד לאיפוס הסיסמה שלך הוא: {code}",
    },
    # --- Chat events ---
    "conversation_summary": {
        "template": "chat/conversation_summary.html",
        "subject": "סיכום שיחה - LinkUp 📋",
        "body": "השיחה שלך הסתיימה. הנה סיכום של הפרטים שנקבעו.",
    },
}
