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

- Commit נכשל אחרי העלאת אובייקט → ניסיון best-effort לנקות orphan prefix החדש (אווטאר).
- CORS לדפדפן על ה-bucket — [`docs/S3_CORS.md`](../S3_CORS.md).

## References

- [`docs/architecture/DATABASE.md`](DATABASE.md)
- [`docs/ENGINEERING_HIGHLIGHTS.md`](../ENGINEERING_HIGHLIGHTS.md)
- [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)
