# שינוי ב-bookings/model.py

הסר את השורה הבאה:
  reminder_sent = Column(Boolean, default=False, server_default="false", nullable=False)

וכן כל שימוש ב-reminder_sent בקובץ (בדוק get_ride_manifest שמציג reminder_sent — הסר את השדה משם גם).
