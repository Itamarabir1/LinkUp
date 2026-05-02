# Alembic – LinkUp Backend

מיגרציות מרוכזות תחת `versions/`. **`env.py`** מייבא `app.db.models` אחרי `Base` כדי ש־`target_metadata` יכלול את מודלי הדומיין שנרשמים דרך registry זה לצורך **`revision --autogenerate`**.

**Docker Compose:** שירות **`migrate`** קורא ל־**`alembic upgrade head`** דרך `ENTRYPOINT` של ה-image (**לא** `uv run`). לפני **backend** וה־workers — ראו [`docs/architecture/DEVELOPMENT.md`](../../docs/architecture/DEVELOPMENT.md). העתק העזר [`db/schema.sql`](../../db/schema.sql) הוא **לייעוץ בלבד**; מקור האמת הוא קבצי **`versions/`**.

## הרצה (מחשב המפתח)

```bash
cd backend
uv run alembic upgrade head
```

אותו מהלך מתוך ה-root של הפרויקט אחרי התקנה ב־`backend/.venv`/uv. פועל על DB ריק או מתקדם בין רוויזיות (מציב head אחיד אחרי **`016_merge015_heads`**).

## אם ה-DB כבר מכיל מיגרציות ישנות

אם מופיעה שגיאה על revision שלא קיים (למשל `normalize_ride_status`):

- **רק לרשום שה-head כבר הוחל (בלי להריץ שוב):**
  ```sql
  UPDATE alembic_version SET version_num = '001_full_schema';
  ```
- **או לאפס ולהריץ את המיגרציה (תוסיף עמודות/טבלאות שחסרות):**
  ```sql
  DELETE FROM alembic_version;
  ```
  ואז:
  ```bash
  uv run alembic upgrade head
  ```
