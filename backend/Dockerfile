# ===== BASE =====
# שכבת בסיס משותפת לשתי הסביבות
FROM python:3.11-slim AS base
WORKDIR /app

# התקנת תלויות מערכת שדרושות ל-PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# העתקת הגדרת הפרויקט והתקנת תלויות
COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install --system -e .

# העתקת שאר הקוד
COPY . .

# ===== DEVELOPMENT =====
# לוקאלי בלבד — uvicorn עם --reload
FROM base AS development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ===== PRODUCTION =====
# פרודקשן — gunicorn בלי --reload
FROM base AS production
ENV WORKERS=2
CMD ["sh", "-c", \
     "alembic upgrade head && \
      gunicorn app.main:app \
      --workers ${WORKERS} \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --timeout 120 \
      --access-logfile -"]
