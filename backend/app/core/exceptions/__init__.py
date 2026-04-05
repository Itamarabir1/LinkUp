# app/core/exceptions/__init__.py
"""ייצוא מרכזי של כל שגיאות הדומיין – שימוש: from app.core.exceptions import LinkupError, UserNotFoundError, ..."""

# Auth
from .auth import (
    GoogleAuthFailed,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidRefreshTokenError,
    InvalidResetCodeError,
    InvalidVerificationCodeError,
    NewPasswordSameAsOldError,
    PasswordsDoNotMatchError,
    PasswordTooWeakError,
    PermissionDeniedError,
    SessionExpiredError,
    UserNotVerifiedError,
    VerificationCodeExpiredError,
)
from .base import LinkupError

# Booking
from .booking import (
    BookingAlreadyExistsError,
    BookingNotFoundError,
    ForbiddenRideActionError,
    NoSeatsAvailableError,
    PassengerRequestNotFoundError,
    RideNotAvailableError,
)

# Chat
from .chat import ChatRoomNotFound, MessageSendFailed, UnauthorizedChatAccess

# Infrastructure
from .infrastructure import (
    CacheConnectionError,
    ExternalServiceError,
    GeocodingError,
    InfrastructureError,
    QueueServiceError,
    RateLimitExceeded,
    RedisUnavailable,
    RouteNotFoundError,
    S3DeleteFailed,
    S3UploadFailed,
    StorageServiceError,
    WorkerTaskFailed,
)

# Notification
from .notification import (
    ContextBuilderError,
    NotificationError,
    RecipientResolverError,
)

# Passenger
from .passenger import (
    ActiveBookingExistsError,
    InsufficientPermissionsForRide,
)

# Ride
from .ride import (
    InvalidDateTimeError,
    InvalidRideStatusError,
    InvalidRouteError,
    RideAlreadyCancelledError,
    RideFullError,
    RideNotFoundError,
)
from .ride import (
    SessionExpiredError as RideSessionExpiredError,
)

# User
from .user import (
    EmailAlreadyRegisteredError,
    PasswordSameAsOldError,
    PhoneAlreadyRegisteredError,
    UserNotFoundError,
)

# Validation
from .validation import (
    FileTooLargeError,
    InsufficientSeatsError,
    InvalidEmailError,
    InvalidFileTypeError,
    InvalidLocationError,
    InvalidPhoneError,
    SameOriginDestinationError,
)

__all__ = [
    "ActiveBookingExistsError",
    "BookingAlreadyExistsError",
    "BookingNotFoundError",
    "CacheConnectionError",
    "ChatRoomNotFound",
    "ContextBuilderError",
    "EmailAlreadyRegisteredError",
    "ExternalServiceError",
    "FileTooLargeError",
    "ForbiddenRideActionError",
    "GeocodingError",
    "GoogleAuthFailed",
    "InfrastructureError",
    "InsufficientPermissionsForRide",
    "InsufficientSeatsError",
    "InvalidCredentialsError",
    "InvalidDateTimeError",
    "InvalidEmailError",
    "InvalidFileTypeError",
    "InvalidLocationError",
    "InvalidPasswordError",
    "InvalidPhoneError",
    "InvalidRefreshTokenError",
    "InvalidResetCodeError",
    "InvalidRideStatusError",
    "InvalidRouteError",
    "InvalidVerificationCodeError",
    "LinkupError",
    "MessageSendFailed",
    "NewPasswordSameAsOldError",
    "NoSeatsAvailableError",
    "NotificationError",
    "PassengerRequestNotFoundError",
    "PasswordSameAsOldError",
    "PasswordTooWeakError",
    "PasswordsDoNotMatchError",
    "PermissionDeniedError",
    "PhoneAlreadyRegisteredError",
    "QueueServiceError",
    "RateLimitExceeded",
    "RecipientResolverError",
    "RedisUnavailable",
    "RideAlreadyCancelledError",
    "RideFullError",
    "RideNotAvailableError",
    "RideNotFoundError",
    "RideSessionExpiredError",
    "RouteNotFoundError",
    "S3DeleteFailed",
    "S3UploadFailed",
    "SameOriginDestinationError",
    "SessionExpiredError",
    "StorageServiceError",
    "UnauthorizedChatAccess",
    "UserNotFoundError",
    "UserNotVerifiedError",
    "VerificationCodeExpiredError",
    "WorkerTaskFailed",
]
