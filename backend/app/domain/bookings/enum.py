import enum


class BookingStatus(str, enum.Enum):
    PENDING = "pending_approval"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    # Active ride lifecycle (driver + passenger)
    EN_ROUTE = "en_route"  # driving to pickup
    ARRIVED = "arrived"  # at pickup point
    TRIP_IN_PROGRESS = "trip_in_progress"  # passenger on board
