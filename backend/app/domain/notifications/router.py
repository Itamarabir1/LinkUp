import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from app.api.dependencies.auth import get_current_user_ws

from app.domain.notifications.services.notification_streamer import notification_streamer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user=Depends(get_current_user_ws),
):
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    await websocket.accept()
    logger.info(f"🔌 WebSocket connection accepted for user: {user_id}")

    try:
        await notification_streamer.stream_user_notifications(websocket, user_id)

    except WebSocketDisconnect:
        logger.info(f"👋 User {user_id} disconnected")
    except Exception as e:
        logger.error(f"❌ Unexpected error in WebSocket for user {user_id}: {e}")
        # כאן אפשר להשתמש ב-LinkupError אם תרצה לעטוף שגיאות תשתית
