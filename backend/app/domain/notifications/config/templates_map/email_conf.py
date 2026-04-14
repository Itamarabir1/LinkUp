EMAIL_MAP = {
    # --- Driver events ---
    "new_ride_request": {
        "template": "NewRideRequest",
        "subject": "בקשת הצטרפות לנסיעה",
        "body": "היי {user_name}, {passenger_name} ביקש/ה להצטרף לנסיעה – {ride_date}. איסוף: {pickup_name}, יעד: {passenger_destination}.",
    },
    "passenger_cancelled": {
        "template": "PassengerCancelled",
        "subject": "עדכון: נוסע ביטל את הצטרפותו לנסיעה ⚠️",
        "body": "היי {user_name}, נוסע ביטל את השתתפותו בנסיעה ל{destination}.",
    },
    "reminder_driver": {
        "template": "RideReminderDriver",
        "subject": "תזכורת לנהג: יוצאים לדרך בעוד שעה! 🛣️",
        "body": "תזכורת: הנסיעה שלך ל{destination} יוצאת בעוד שעה.",
    },
    # --- Passenger events ---
    "ride_created_for_passengers": {
        "template": "RideCreatedForPassengers",
        "subject": "נסיעה חדשה שמתאימה לך – מ{origin} ל{destination} 🚗",
        "body": "היי {user_name}, נרשמה נסיעה מ{origin} ל{destination} שיוצאת ב{ride_date}. לחץ/י לצפייה ובקשת הצטרפות.",
    },
    "booking_confirmed": {
        "template": "BookingApproved",
        "subject": "איזה כיף! הנסיעה שלך אושרה ✅",
        "body": "היי {user_name}, הנהג אישר את בקשתך לנסיעה ל{destination}!",
    },
    "booking_rejected": {
        "template": "BookingRejected",
        "subject": "עדכון לגבי בקשת הנסיעה שלך ℹ️",
        "body": "היי {user_name}, לצערנו הבקשה לנסיעה ל{destination} לא אושרה.",
    },
    "ride_cancelled_by_driver": {
        "template": "RideCancelledByDriver",
        "subject": "עדכון דחוף: הנסיעה בוטלה על ידי הנהג 🛑",
        "body": "הודעה דחופה: הנסיעה ל{destination} בוטלה על ידי הנהג.",
    },
    "reminder_passenger": {
        "template": "RideReminderPassenger",
        "subject": "הנסיעה שלך יוצאת בעוד שעה! 🚗",
        "body": "היי {user_name}, תזכורת: הנסיעה שלך ל{destination} יוצאת בעוד שעה.",
    },
    # --- Auth & user lifecycle ---
    "welcome": {
        "template": "Welcome",
        "subject": "ברוכים הבאים ל-LinkUp! 🎉",
        "body": "היי {user_name}, ברוך הבא לקהילת LinkUp! איזה כיף שהצטרפת.",
    },
    "email_verification": {
        "template": "VerifyEmail",
        "subject": "אימות כתובת המייל שלך - LinkUp 🛡️",
        "body": "קוד האימות שלך ל-LinkUp הוא: {code}",
    },
    "password_reset_code": {
        "template": "PasswordReset",
        "subject": "קוד לאיפוס הסיסמה שלך - LinkUp 🔑",
        "body": "הקוד לאיפוס הסיסמה שלך הוא: {code}",
    },
    # --- Chat events ---
    "conversation_summary": {
        "template": "ConversationSummary",
        "subject": "סיכום שיחה - LinkUp 📋",
        "body": "השיחה שלך הסתיימה. הנה סיכום של הפרטים שנקבעו.",
    },
}
