#!/usr/bin/env bash
# Render.com / Docker startup script for the PointCV backend.
#
# NOTE: Better Auth (frontend app) owns its own tables (user, session,
# account, verification). Alembic only manages PointCV's business tables
# (users, packages, orders, ...) so the two never conflict — but migrations
# MUST finish before uvicorn starts serving requests.
set -e

echo ">>> [PointCV] Starting deployment script"

echo ">>> [PointCV] Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo ">>> [PointCV] Seeding catalog data (idempotent)..."
python run_seed.py

PORT="${PORT:-10000}"
WORKERS="${WEB_CONCURRENCY:-1}"
echo ">>> [PointCV] Starting uvicorn on 0.0.0.0:${PORT} with ${WORKERS} worker(s)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers "${WORKERS}"
