# ---- Stage 1: builder ----
# gcc + libpq-dev are required to compile asyncpg / psycopg2 wheels on Alpine.
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.11/site-packages"  # <-- TAMBAH INI

WORKDIR /app

# libpq is needed at runtime by asyncpg/psycopg2; curl for health checks.
RUN apt-get update \
  && apt-get install -y --no-install-recommends libpq5 curl \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --gid 1001 app \
  && useradd --system --uid 1001 --gid app app

COPY --from=builder /install /install

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Writable dir for SQLite (platform volumes mount here, e.g. Fly.io /app/data).
RUN mkdir -p /app/data && chown -R app:app /app/data

USER app
EXPOSE 8000

# Migrations are applied by the entrypoint (see docker-compose command).
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
