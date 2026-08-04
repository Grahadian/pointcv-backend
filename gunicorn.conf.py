"""Gunicorn production configuration for PointCV API."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

workers = int(os.environ.get("WEB_CONCURRENCY", 4))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts for slow clients / SSE keep-alive.
timeout = 60
graceful_timeout = 30
keepalive = 5

# Logging.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
capture_output = True

# Restart workers that crash (helps with asyncpg connection churn).
max_requests = 1000
max_requests_jitter = 100
