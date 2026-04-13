"""
Shared constants for the whole project.
Values that appear in more than one file — single source of truth.
"""

# Batch sizes
BATCH_SIZE_DEFAULT = 100  # תזכורות, outbox, ניתוח צ'אט, ייצוא

# Redis TTL (seconds)
RIDE_PREVIEW_TTL = 86400  # 24 שעות
OTP_TTL = 600  # 10 דקות
GEOCODE_CACHE_TTL = 86400  # 24 שעות
