#!/bin/sh
set -e

# Legacy entrypoint — prefer render-start.sh (migrate + seed + serve).
# Run migration
alembic upgrade head

# Exec replaces the shell process (low memory usage).
# Single process mode unless WEB_CONCURRENCY is set.
PORT="${PORT:-10000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers "${WEB_CONCURRENCY:-1}"
