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
# Docker Compose: workers מ-UVICORN_WORKERS ב-backend/.env (shell בתוך הקונטיינר)
FROM base AS development
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# ===== MIGRATE =====
# שירות חד-פעמי: alembic בלבד — בלי entrypoint של uvicorn
FROM base AS migrate
ENTRYPOINT ["alembic"]
CMD ["upgrade", "head"]

# ===== WORKER =====
# outbox-worker — בלי entrypoint של uvicorn
FROM base AS worker
CMD ["python", "-m", "app.workers.main_worker"]

# ===== PRODUCTION =====
# פרודקשן — gunicorn בלי --reload
FROM base AS production
ENV WORKERS=2
CMD ["sh", "-c", \
     "gunicorn app.main:app \
      --workers ${WORKERS} \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --timeout 120 \
      --access-logfile -"]
