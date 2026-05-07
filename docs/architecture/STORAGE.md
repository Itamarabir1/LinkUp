# Storage Architecture

מדיה ואובייקטים ב-S3 ממומשים דרך שכבת **`app/infrastructure/s3/`** + לוגיקת דומיין (קבוצות / פרופיל). מסמך זה מתאר את הזרימה העיקרית; פירוט טבלאות — [`DATABASE.md`](DATABASE.md).

## Upload path (presigned)

- **לקוח** מקבל URL חתום מה-API, מעלה ישירות ל-S3 — ה-byte stream לא עובר דרך Uvicorn. מימוש: `client.py` / `service.py` תחת `infrastructure/s3/`.
- **קבוצות / אווטאר:** השירות הרלוונטי יוצר staging key ואז מתזמן עיבוד (אווטאר: תור **`avatar_upload_queue`** — ראו `workers/tasks/avatar_tasks.py`, `image_processor.py`).

## Avatar versioning

- Prefix יציב למשתמש בדומיין: **`avatars/{user_id}/v{version}/`** עם מעבר גרסה ב-DB (**`users.avatar_key`**) לאחר הצלחה; מחיקת גרסה קודמת אחרי commit (כפי מתועד בפרק upload ב-[`ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md)).

## קריאה (GET)

- עם **`CLOUDFRONT_DOMAIN`**: HTTPS ליציבות ו-cache.
- ללא דומיין: **presigned GET** ישירות ל-S3.

## Cleanup / edge cases

- **מחיקת prefix**: `StorageService.list_and_delete_prefix` מזרימה מפתחות דרך `S3Client.iter_prefix_keys` (בלי טעינת הרשימה המלאה לזיכרון) וקוראת ל-**`delete_objects`** בחבילות של עד 1000 מפתחות (`S3_DELETE_OBJECTS_MAX_KEYS` ב-[`backend/app/infrastructure/s3/client.py`](../../backend/app/infrastructure/s3/client.py)).
- **הסרת אווטאר מפרופיל**: ה-API מנקה שדות `users.avatar_*` ומפרסם **`user.avatar_remove`** ל-Outbox באותה טרנזקציה; `task-worker` / `avatar_upload_queue` קורא ל-`delete_user_avatar_folder` (ראו [`avatar_tasks.py`](../../backend/app/workers/tasks/avatar_tasks.py)). כך זמן בקשת HTTP לא תלוי בנפח אובייקטים תחת `avatars/{user_id}/`.
- Commit נכשל אחרי העלאת אובייקט → ניסיון best-effort לנקות orphan prefix החדש (אווטאר).
- CORS לדפדפן על ה-bucket — [`docs/S3_CORS.md`](../S3_CORS.md).

## References

- [`docs/architecture/DATABASE.md`](DATABASE.md)
- [`docs/ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md)
- [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)
