# ---- Stage 1: builder ----
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --prefix=/install -r requirements.txt

# ---- Stage 2: runtime ----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PATH="/install/bin:$PATH"
ENV PYTHONPATH="/install/lib/python3.11/site-packages"

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends libpq5 curl \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd --gid 1001 app \
  && useradd --system --uid 1001 --gid app app

COPY --from=builder /install /install

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN mkdir -p /app/data && chown -R app:app /app/data

USER app
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
