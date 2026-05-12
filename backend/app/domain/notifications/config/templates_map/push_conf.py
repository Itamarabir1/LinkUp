PUSH_TEMPLATES = {
    "new_ride_request": {
        "title": "בקשת הצטרפות לנסיעה",
        "body": "{passenger_name} ביקש/ה להצטרף – {ride_date}, איסוף: {pickup_name}, יעד: {passenger_destination}.",
    },
    "passenger_cancelled": {
        "title": "ביטול נוסע",
        "body": "עדכון: {passenger_name} ביטל את השתתפותו בנסיעה ל{destination}.",
    },
    "booking_confirmed": {
        "title": "הנסיעה אושרה! ✅",
        "body": "איזה כיף, הנהג {driver_name} אישר את בקשתך.",
    },
    "booking_rejected": {
        "title": "בקשת ההצטרפות לא אושרה",
        "body": "לצערנו הנהג לא אישר את בקשתך לנסיעה ל{destination}.",
    },
    "ride_cancelled_by_driver": {
        "title": "הנסיעה בוטלה 🛑",
        "body": "לצערנו הנהג ביטל את הנסיעה ל{destination}.",
    },
    "reminder_passenger": {
        "title": "⏰ תזכורת לנסיעה",
        "body": "הנסיעה ל-{destination} מתחילה בעוד 30 דקות!",
    },
    "reminder_driver": {
        "title": "⏰ תזכורת לנסיעה",
        "body": "הנסיעה שלך ל-{destination} מתחילה בעוד 30 דקות!",
    },
    "ride_created_for_passengers": {
        "title": "🚗 נסיעה חדשה זמינה!",
        "body": "נסיעה ל-{destination} ב-{ride_date}. לחץ להצטרף.",
    },
    "chat_message": {
        "title": "הודעה מ-{sender_name}",
        "body": "{message_preview}",
    },
}
