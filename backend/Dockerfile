# ===== BASE =====
FROM python:3.11-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir uv && uv pip install --system -e .

COPY . .

# ===== DEVELOPMENT =====
FROM base AS development
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# ===== MIGRATE =====
FROM base AS migrate
ENTRYPOINT ["alembic"]
CMD ["upgrade", "head"]

# ===== WORKER =====
FROM base AS worker
CMD ["python", "-m", "app.workers.main_worker"]

# ===== PRODUCTION =====
FROM base AS production
ENV WORKERS=2
CMD ["sh", "-c", \
     "gunicorn app.main:app \
      --workers ${WORKERS} \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --timeout 120 \
      --access-logfile -"]
