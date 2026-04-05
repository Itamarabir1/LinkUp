from fastapi import UploadFile

from app.core.utils.validators import validate_avatar_file


async def validate_avatar(file: UploadFile) -> UploadFile:
    """
    Dependency: בודק שאווטאר תקין (סוג קובץ + גודל מקסימלי).
    הכללים מוגדרים ב-core/utils/validators (MAX_AVATAR_SIZE_MB, ALLOWED_AVATAR_CONTENT_TYPES).
    """
    validate_avatar_file(file)
    return file


# וולידטור גנרי למסמכים/סוגי קבצים אחרים (גודל וסוג שונים)
def file_validator(allowed_types: tuple[str, ...], max_size_mb: int):
    """מחזיר Dependency שבודק סוג קובץ וגודל (למשל למסמכים)."""
    from app.core.exceptions.validation import FileTooLargeError, InvalidFileTypeError

    async def _validate(file: UploadFile) -> UploadFile:
        if file.content_type not in allowed_types:
            raise InvalidFileTypeError(content_type=file.content_type or "")
        max_bytes = max_size_mb * 1024 * 1024
        actual_size = getattr(file, "size", 0) or 0
        if actual_size > max_bytes:
            raise FileTooLargeError(max_size_mb=max_size_mb)
        return file

    return _validate


validate_document = file_validator(
    allowed_types=("application/pdf", "image/jpeg", "image/png"),
    max_size_mb=10,
)
