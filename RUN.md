# איך להריץ את הפרויקט LinkUp

צריך **שני חלונות CMD** – אחד לבקאנד ואחד לפרונט.

---

## שלב 0: וידוא מיקום הפרויקט

דוגמה לנתיב (החלף לנתיב אצלך):
```
c:\Users\user\Desktop\LinkUp
```
בתוכו צריכות להיות לפחות תיקיות: `backend`, `frontend`. ל**צ'אט בזמן אמת**, **התראות in-app** (פיד), **push דרך worker** וכו' — צריך גם תשתית (Postgres, Redis, RabbitMQ), ולרוב **chat-ws** על פורט **8081**; השורה המלאה: **`README.md`** / **`docs/architecture/DEVELOPMENT.md`** עם `docker compose up -d`.

---

## שלב 1: הרצת הבקאנד (API)

**חשוב:** אם **Docker רץ** (למשל `docker compose up -d`), **מיכל הבקאנד** של LinkUp תופס פורט 8000. אז הבקשות מהאתר מגיעות למיכל (קוד ישן) ולא ל-uvicorn שהרצת ב-CMD – ולכן אין לוגים. **עצור את מיכל הבקאנד:**
```cmd
docker stop linkup_backend
```
אחר כך הרץ את הבקאנד **מקומית** (למטה). שאר המיכלים (db, redis, rabbitmq) יכולים להמשיך לרוץ.

**אם אין לך שום לוג כשאתה מנסה להירשם** – כנראה ש**תהליך אחר** תופס פורט 8000 (מיכל Docker או בקאנד ישן). הפתרון:

1. **לסגור את כל חלונות CMD** שקשורים לפרויקט.

2. **להריץ את הבקאנד דרך הקובץ המוכן** (הוא עוצר תהליך קיים על 8000 ואז מפעיל את הבקאנד):
   - פתח סייר קבצים → `c:\Users\user\Desktop\LinkUp\backend`
   - **לחיצה כפולה** על `run-backend.bat`

   או מ-CMD:
   ```cmd
   c:\Users\user\Desktop\LinkUp\backend\run-backend.bat
   ```

3. **אם אתה מעדיף להריץ ידנית** (בלי הסקריפט):
   - לפתוח CMD
   - `cd c:\Users\user\Desktop\LinkUp\backend`
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

4. **לבדוק שהבקאנד עלה:**
   - אמורות להופיע שורות כמו:
     ```
     [LinkUp] Backend נטען (main.py) – CORS + לוגים פעילים
     INFO:     Uvicorn running on http://0.0.0.0:8000
     ```
   - אם **לא** מופיע "LinkUp Backend נטען" – יש שגיאת הפעלה (למשל חסר Python/uvicorn או שגיאה ב־import). תעתיק את השגיאה המלאה.

5. **אל תסגור את החלון** – הבקאנד צריך להמשיך לרוץ.

---

## שלב 2: הרצת הפרונט (אתר)

1. **לפתוח חלון CMD שני** (עוד אחד).

2. **לעבור לתיקיית הפרונט:**
   ```cmd
   cd c:\Users\user\Desktop\LinkUp\frontend
   ```

3. **הפעלה (פעם ראשונה – התקנת חבילות):**
   ```cmd
   npm install
   npm run dev
   ```
   אם כבר הרצת `npm install` בעבר, מספיק:
   ```cmd
   npm run dev
   ```

4. **לבדוק:** אמורה להופיע שורה כמו:
   ```
   ➜  Local:   http://localhost:5173/
   ```

5. **לפתוח בדפדפן:**  
   [http://localhost:5173](http://localhost:5173)

---

## סיכום

| חלון | פקודה | כתובת |
|------|--------|--------|
| CMD 1 (בקאנד) | `cd c:\Users\user\Desktop\LinkUp\backend` ואז `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | API: http://localhost:8000 |
| CMD 2 (פרונט) | `cd c:\Users\user\Desktop\LinkUp\frontend` ואז `npm run dev` | אתר: http://localhost:5173 |

---

## אם הבקאנד לא עולה

- **"uvicorn לא מזוהה"** – להתקין:  
  `pip install uvicorn`  
  (רצוי בתוך סביבה וירטואלית: `python -m venv venv` ואז `venv\Scripts\activate` ואז `pip install -r requirements.txt`).

- **שגיאה על חוסר מודול (module)** – מתוך `backend` להריץ:  
  `pip install -r requirements.txt`

- **שגיאה על DB / Redis / RabbitMQ / chat-ws / worker** – להריץ את התשתית (למשל עם Docker) משורש הפרויקט (`LinkUp`):  
  `docker compose up -d` — מרים `db`, `redis`, `rabbitmq`, שירות **`migrate`** (מיגרציה אוטומטית), `chat-ws`, `outbox-worker`, `backend` וכו׳ (ללא **nginx** אלא אם מריצים `docker compose --profile prod up -d`). אם **`migrate`** נכשל — לבדוק `docker compose logs migrate`; **backend** לא יעלה עד שהמיגרציה מצליחה.  
  אפשר גם במפורש: `docker compose up -d db redis rabbitmq chat-ws` אם צריך רק חלק מהשירותים (אז מיגרציה ידנית: `cd backend && alembic upgrade head`).

---

## אחרי שהכל רץ

כשאתה מנסה **הרשמה** באתר, **בחלון CMD של הבקאנד** (החלון הראשון) אמורות להופיע שורות כמו:

```
[LinkUp] >>> בקשה הגיעה: POST /api/v1/auth/register
[LinkUp] register endpoint – מתחיל register_new_user
```

אם יש שגיאה 500, תופיע גם שורת `[LinkUp] !!! שגיאה 500:` ואחריה פרטי השגיאה.

---

## הרחבות (אופציונלי)

| צורך | מה להרים |
|------|-----------|
| צ'אט + typing + presence | **chat-ws** (למשל דרך Docker על **8081**) — ראו `chat-ws/README.md` |
| פיד התראות חי בווב + WebSocket נסיעות/מיקום | **backend** על **8000** עם Redis; הפרונט מתחבר ל־`ws://localhost:8000/api/v1/...` — ראו `frontend/src/config/env.ts` |
| מיגרציות DB | `cd backend && alembic upgrade head` או שירות **`migrate`** ב־Compose — `backend/alembic/README.md` |
