# ===== BUILDER =====
# Installs build tools + all Python dependencies. Used as base for development.
FROM python:3.11-slim AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir uv \
    && uv pip install --system .

# ===== RUNTIME =====
# Clean image without build tools. Base for production, worker, and migrate.
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# ===== DEVELOPMENT =====
FROM builder AS development
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# ===== MIGRATE =====
FROM runtime AS migrate
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/
RUN chown -R appuser:appgroup /app
USER appuser
ENTRYPOINT ["alembic"]
CMD ["upgrade", "head"]

# ===== WORKER =====
FROM runtime AS worker
COPY app/ ./app/
RUN chown -R appuser:appgroup /app
USER appuser
CMD ["python", "-m", "app.workers.notification_worker"]

# ===== PRODUCTION =====
FROM runtime AS production
COPY app/ ./app/
RUN chown -R appuser:appgroup /app
USER appuser
ENV WORKERS=1
CMD ["sh", "-c", \
     "gunicorn app.main:app \
      --workers ${WORKERS} \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --timeout 120 \
      --access-logfile -"]
