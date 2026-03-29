import uuid
from typing import Any, Dict, Optional


class LinkupError(Exception):
    """בסיס לכל שגיאות הדומיין – מאפשר handler מרכזי ומעקב (trace_id)."""

    message: str = "שגיאת מערכת"
    status_code: int = 400
    error_code: str = "GENERIC_ERROR"

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        # תאימות לאחור: detail נחשב כ-message
        if kwargs.get("detail") is not None and message is None:
            message = kwargs["detail"] if isinstance(kwargs["detail"], str) else str(kwargs["detail"])
        self.message = message or getattr(self, "message", "שגיאת מערכת")
        self.status_code = status_code if status_code is not None else getattr(self, "status_code", 400)
        self.error_code = error_code or getattr(self, "error_code", "GENERIC_ERROR")
        self.payload = payload if payload is not None else {}
        self.trace_id = str(uuid.uuid4())
        super().__init__(self.message)
