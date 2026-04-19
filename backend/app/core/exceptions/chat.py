from .base import LinkUpError


class ChatRoomNotFound(LinkUpError):
    status_code = 404
    error_code = "CHAT_ROOM_NOT_FOUND"
    message = "שיחה לא נמצאה"


class UnauthorizedChatAccess(LinkUpError):
    status_code = 403
    error_code = "CHAT_UNAUTHORIZED_ACCESS"
    message = "אין הרשאה לגשת לשיחה זו"


class MessageSendFailed(LinkUpError):
    status_code = 500
    error_code = "CHAT_MESSAGE_SEND_FAILED"
    message = "שליחת ההודעה נכשלה"
