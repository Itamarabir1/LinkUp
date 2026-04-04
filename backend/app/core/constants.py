"""
קבועים משותפים לכל הפרויקט.
ערכים שמופיעים ביותר מקובץ אחד — מקור אמת יחיד.
"""

# Batch sizes
BATCH_SIZE_DEFAULT = 100  # תזכורות, outbox, ניתוח צ'אט, ייצוא

# Redis TTL (שניות)
RIDE_PREVIEW_TTL = 86400  # 24 שעות
OTP_TTL = 600  # 10 דקות
GEOCODE_CACHE_TTL = 86400  # 24 שעות
