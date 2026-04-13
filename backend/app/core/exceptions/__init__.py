# app/core/exceptions/__init__.py
"""Central re-exports for domain errors: ``from app.core.exceptions import LinkupError, ...``."""

# Admin
from .admin import (
    AdminAccessRequiredError,
    OutboxEventNotFoundError,
    OutboxRequeueInvalidStatusError,
)

# Auth
from .auth import (
    GoogleAuthFailed,
    InvalidAccessTokenError,
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
    UserInactiveOrMissingError,
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

# Group
from .group import (
    GroupAdminRequiredError,
    GroupFilterAuthRequiredError,
    GroupInvalidImageKeyError,
    GroupMemberNotFoundError,
    GroupNotFoundError,
    GroupNotMemberError,
)

# Infrastructure
from .infrastructure import (
    CacheConnectionError,
    ExternalServiceError,
    GeocodingError,
    InfrastructureError,
    InternalServerError,
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
    BadRequestError,
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
    "AdminAccessRequiredError",
    "BadRequestError",
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
    "GroupAdminRequiredError",
    "GroupFilterAuthRequiredError",
    "GroupInvalidImageKeyError",
    "GroupMemberNotFoundError",
    "GroupNotFoundError",
    "GroupNotMemberError",
    "InfrastructureError",
    "InternalServerError",
    "InvalidAccessTokenError",
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
    "OutboxEventNotFoundError",
    "OutboxRequeueInvalidStatusError",
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
    "UserInactiveOrMissingError",
    "UserNotFoundError",
    "UserNotVerifiedError",
    "VerificationCodeExpiredError",
    "WorkerTaskFailed",
]
