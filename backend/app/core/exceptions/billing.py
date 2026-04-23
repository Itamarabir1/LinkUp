from app.core.exceptions.base import LinkUpError


class PaymentNotFoundError(LinkUpError):
    message = "תשלום לא נמצא"
    status_code = 404
    error_code = "PAYMENT_NOT_FOUND"

    def __init__(self, payment_id: str | None = None):
        super().__init__(message=f"תשלום {payment_id} לא נמצא" if payment_id else self.message)


class PaymentAlreadyExistsError(LinkUpError):
    message = "תשלום כבר קיים"
    status_code = 409
    error_code = "PAYMENT_ALREADY_EXISTS"


class StripeWebhookError(LinkUpError):
    message = "שגיאה באימות webhook"
    status_code = 400
    error_code = "STRIPE_WEBHOOK_ERROR"


class CheckoutSessionError(LinkUpError):
    message = "שגיאה ביצירת סשן תשלום"
    status_code = 502
    error_code = "CHECKOUT_SESSION_ERROR"


class UserAlreadyPremiumError(LinkUpError):
    message = "המשתמש כבר פרמיום"
    status_code = 400
    error_code = "USER_ALREADY_PREMIUM"
