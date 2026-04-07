# Alembic – Linkup Backend

מיגרציות מרוכזות תחת `versions/`. **`env.py`** מייבא `app.db.models` אחרי `Base` כדי ש־`target_metadata` יכלול את מודלי הדומיין שנרשמים דרך registry זה לצורך **`revision --autogenerate`**.

## הרצה

```bash
alembic upgrade head
```

פעם אחת. פועל על DB ריק (יוצר את כל הטבלאות) או על DB קיים (מוסיף רק מה שחסר – idempotent).

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
  alembic upgrade head
  ```
