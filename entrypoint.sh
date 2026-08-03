#!/bin/sh
set -e

# Run migration
alembic upgrade head

# Exec menggantikan shell process (hemat memory)
# Tanpa --workers = single process mode
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
