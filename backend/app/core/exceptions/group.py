from uuid import UUID

from .base import LinkUpError


class GroupNotFoundError(LinkUpError):
    status_code = 404
    error_code = "GROUP_NOT_FOUND"
    message = "קבוצה לא נמצאה"

    def __init__(self, group_id: UUID | str | None = None):
        payload = {"group_id": str(group_id)} if group_id is not None else None
        super().__init__(payload=payload)


class GroupNotMemberError(LinkUpError):
    status_code = 403
    error_code = "GROUP_NOT_MEMBER"
    message = "אינך חבר בקבוצה"


class GroupAdminRequiredError(LinkUpError):
    status_code = 403
    error_code = "GROUP_ADMIN_REQUIRED"
    message = "רק אדמין הקבוצה יכול לבצע פעולה זו"


class GroupInvalidImageKeyError(LinkUpError):
    status_code = 400
    error_code = "GROUP_INVALID_IMAGE_KEY"
    message = "מפתח תמונה לא תקין"


class GroupMemberNotFoundError(LinkUpError):
    status_code = 404
    error_code = "GROUP_MEMBER_NOT_FOUND"
    message = "חבר לא נמצא בקבוצה"

    def __init__(self, user_id: UUID | str | None = None):
        payload = {"user_id": str(user_id)} if user_id is not None else None
        super().__init__(payload=payload)


class GroupFilterAuthRequiredError(LinkUpError):
    """Search or operation with group_id requires a logged-in user."""

    status_code = 401
    error_code = "GROUP_AUTH_REQUIRED"
    message = "נדרשת התחברות לגישה לקבוצה"
