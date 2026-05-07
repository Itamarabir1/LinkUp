"""
Shared constants for the whole project.
Values that appear in more than one file — single source of truth.
"""

# Batch sizes
BATCH_SIZE_DEFAULT = 100  # תזכורות, outbox, ניתוח צ'אט, ייצוא

# Driver ride manifest — single ORDER BY rank + LIMIT (confirmed before pending)
MANIFEST_BOOKING_ROW_LIMIT = 100

# Spatial match cap: heavy PostGIS query — keep low
IMMEDIATE_MATCH_LIMIT = 20

# GET /passengers/me pagination
PASSENGER_REQUESTS_DEFAULT_LIMIT = 50
PASSENGER_REQUESTS_MAX_LIMIT = 200

# GET /users/me/notifications pagination
NOTIFICATIONS_DEFAULT_LIMIT = 20
NOTIFICATIONS_MAX_LIMIT = 100

# Redis TTL (seconds)
RIDE_PREVIEW_TTL = 86400  # 24 שעות
OTP_TTL = 600  # 10 דקות
GEOCODE_CACHE_TTL = 86400  # 24 שעות
