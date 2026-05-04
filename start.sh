#!/usr/bin/env bash
set -e
PORT=${PORT:-10000}
if [ -x "/opt/render/project/src/.venv/bin/gunicorn" ]; then
  exec /opt/render/project/src/.venv/bin/gunicorn -w 1 --threads 100 -b 0.0.0.0:${PORT} app:app
fi
if command -v gunicorn >/dev/null 2>&1; then
  exec gunicorn -w 1 --threads 100 -b 0.0.0.0:${PORT} app:app
fi
exec python -m gunicorn -w 1 --threads 100 -b 0.0.0.0:${PORT} app:app
